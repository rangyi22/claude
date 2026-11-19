import base64
import json

import httpx
import pytest

from md2short import photo_engine as pe

PNG = base64.b64encode(b"\x89PNG-fake").decode()
WORDS = [
    {"text": "트럼프가", "start": 0, "end": 400},
    {"text": "합의를", "start": 400, "end": 800},
    {"text": "했다.", "start": 800, "end": 1200},
    {"text": "코스피가", "start": 1300, "end": 1700},
    {"text": "올랐다.", "start": 1700, "end": 2100},
]


def _responses_ok(req, n):
    body = json.loads(req.content)
    n = body["text"]["format"]["schema"]["properties"]["prompts"]["minItems"]
    out = json.dumps({"prompts": [f"photo prompt {i}" for i in range(n)]})
    return httpx.Response(200, json={"output_text": out})


def _image_ok():
    return httpx.Response(200, json={"data": [{"b64_json": PNG}]})


def _blocked():
    return httpx.Response(400, json={"error": {"code": "moderation_blocked", "message": "no"}})


def make(handler):
    calls = []

    def wrap(req):
        calls.append(req)
        return handler(req)

    return httpx.Client(transport=httpx.MockTransport(wrap)), calls


def default_handler(req):
    if req.url.path.endswith("/responses"):
        return _responses_ok(req, 0)
    return _image_ok()


def run(tmp_path, client, **kw):
    stages = []
    cues = pe.plan_photo_cues(
        WORDS, job_id="j1", api_key="k", root=tmp_path, on_stage=stages.append, client=client, max_workers=1, **kw
    )
    return cues, stages


def test_hints_trump():
    h = pe.extract_visual_hints("트럼프가 합의를 했다")
    assert h["primary_visual_subject"] == "Donald Trump"
    assert "diplomatic agreement table" in h["visual_keywords"]


def test_hints_company_and_fallback():
    assert pe.extract_visual_hints("엔비디아 실적")["primary_visual_subject"] == "Nvidia"
    assert pe.extract_visual_hints("안녕하세요")["visual_keywords"]


def test_keyword_focus_prefix():
    assert pe._apply_keyword_focus("a desk", "Donald Trump") == "Primary visual subject: Donald Trump. a desk"
    assert pe._apply_keyword_focus("Donald Trump at a desk", "Donald Trump") == "Donald Trump at a desk"


def test_sanitise_removes_names():
    out = pe._sanitise_prompt("Trump and 트럼프 meet Nvidia during war")
    for bad in ("Trump", "트럼프", "Nvidia", "war"):
        assert bad.lower() not in out.lower()


def test_batch_prompt_request_shape_single_call(tmp_path):
    client, calls = make(default_handler)
    cues, _ = run(tmp_path, client)
    resp_calls = [c for c in calls if c.url.path.endswith("/responses")]
    assert len(resp_calls) == 1
    body = json.loads(resp_calls[0].content)
    assert body["model"] == "gpt-5-mini"
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["schema"]["properties"]["prompts"]["minItems"] == 2
    assert "Donald Trump" in body["input"][1]["content"]
    assert len(cues) == 2


def test_images_saved_and_cue_fields(tmp_path):
    client, calls = make(default_handler)
    cues, stages = run(tmp_path, client)
    img = [c for c in calls if c.url.path.endswith("/images/generations")]
    assert len(img) == 2
    b = json.loads(img[0].content)
    assert (b["model"], b["size"], b["quality"]) == ("gpt-image-2", "1024x1536", "high")
    c0, c1 = cues
    assert c0["emoticonFileName"].startswith("jobs/j1/photos/seg_01_")
    assert c1["emoticonFileName"].startswith("jobs/j1/photos/seg_02_")
    assert (tmp_path / "remotion" / "public" / c0["emoticonFileName"]).read_bytes() == b"\x89PNG-fake"
    assert (c0["startMs"], c0["durationMs"]) == (0, 1300)
    assert (c1["startMs"], c1["durationMs"]) == (1300, 800)
    assert c0["assetKind"] == c0["visualMode"] == "photo"
    assert c0["primaryVisualSubject"] == "Donald Trump"
    assert c0["promptStage"] == "original" and c0["moderationBlocked"] == 0
    assert c0["prompt"].startswith("Primary visual subject: Donald Trump.")


def test_cache_hit_skips_http(tmp_path):
    client, _ = make(default_handler)
    first, _ = run(tmp_path, client)
    client2, calls2 = make(default_handler)
    second, _ = run(tmp_path, client2)
    assert [c for c in calls2 if c.url.path.endswith("/images/generations")] == []
    assert [c["emoticonFileName"] for c in first] == [c["emoticonFileName"] for c in second]


def test_moderation_chain_progression(tmp_path):
    def handler(req):
        if req.url.path.endswith("/responses"):
            return _responses_ok(req, 0)
        prompt = json.loads(req.content)["prompt"]
        if "Trump" in prompt:
            return _blocked()
        return _image_ok()

    client, _ = make(handler)
    cues, _ = run(tmp_path, client)
    assert cues[0]["promptStage"] == "sanitised"
    assert cues[0]["moderationBlocked"] == 1
    assert "trump" not in cues[0]["prompt"].lower()

    def handler2(req):
        if req.url.path.endswith("/responses"):
            return _responses_ok(req, 0)
        prompt = json.loads(req.content)["prompt"]
        return _image_ok() if prompt == pe._SAFE_FALLBACK_PROMPT else _blocked()

    client2, _ = make(handler2)
    cues2, _ = run(tmp_path / "b", client2)
    assert all(c["promptStage"] == "safe_fallback" for c in cues2)
    assert cues2[0]["moderationBlocked"] == 2


def test_all_blocked_raises(tmp_path):
    def handler(req):
        if req.url.path.endswith("/responses"):
            return _responses_ok(req, 0)
        return _blocked()

    client, _ = make(handler)
    with pytest.raises(pe.PhotoEngineError):
        run(tmp_path, client)


def test_on_stage_order(tmp_path):
    client, _ = make(default_handler)
    _, stages = run(tmp_path, client)
    assert stages == ["photo_generating", "photos_generated"]


def test_prompt_count_mismatch(tmp_path):
    def handler(req):
        return httpx.Response(200, json={"output_text": json.dumps({"prompts": ["only one"]})})

    client, _ = make(handler)
    with pytest.raises(pe.PhotoEngineError):
        run(tmp_path, client)


def test_generate_image_moderation_typed(tmp_path):
    client, _ = make(lambda r: _blocked())
    with pytest.raises(pe.ModerationBlockedError):
        pe.generate_image("x", "k", tmp_path / "a.png", client)


def test_storyboard_image_prompt_used_directly(tmp_path):
    segs = [{"index": 0, "startMs": 0, "endMs": 1000, "text": "x", "image_prompt": "my direct prompt"}]
    client, calls = make(default_handler)
    cues = pe.plan_photo_cues(WORDS, job_id="j", api_key="k", segments=segs, root=tmp_path, client=client)
    assert not [c for c in calls if c.url.path.endswith("/responses")]
    assert cues[0]["prompt"] == "my direct prompt"
