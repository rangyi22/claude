"""pipeline / CLI 통합 테스트. 외부 API(ElevenLabs/OpenAI)는 모두 가짜로 교체한다."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from md2short import cli, opening, photo_engine, pipeline, render, state, transcript, voice
from md2short.schema import JobConfig

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 필요")

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample.md"
AUDIO_MS = 6000

STORYBOARD_MD = """# 스토리보드

### 1컷
- 자막: 미국 증시가 상승했습니다.
- 화면 연출: 호랑이가 로켓을 타고 가즈아
- 이미지 프롬프트: stock market rally chart

### 2컷
- 자막: 애플이 3.2% 올랐습니다.
- 화면 연출: 실적 호조
- 이미지 프롬프트: apple earnings
"""


def _words():
    texts = ["십일월", "이십일", "데이브리핑입니다.", "미국", "증시가", "상승했습니다.", "애플이", "삼점이", "퍼센트", "올랐습니다."]
    out, t = [], 0
    for text in texts:
        out.append({"text": text, "start": t, "end": t + 450})
        t += 560
    return out


def _make_audio(path: Path, ms: int = AUDIO_MS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={ms / 1000}", "-c:a", "libmp3lame", str(path)],
        check=True,
    )


def _make_video(path: Path, ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=white:s=1080x1920:r=30:d={ms / 1000}", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


@pytest.fixture
def fake_apis(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(pipeline.env, "load_env", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(render, "ensure_remotion_available", lambda root=None: None)
    calls = {"tts": [], "render": []}

    def fake_synthesize(text, voice_id, out_path, api_key, speed=1.0, log_dir=None, client=None):
        calls["tts"].append(text)
        _make_audio(Path(out_path))
        if log_dir:
            (Path(log_dir) / "tts_input.txt").write_text(text, encoding="utf-8")
        return Path(out_path)

    def fake_transcribe(audio_path, api_key, *, audio_duration_ms, language="ko", out_path=None, raw_log_path=None, client=None):
        if raw_log_path:
            Path(raw_log_path).write_text("{}", encoding="utf-8")
        return {"language_code": "kor", "audio_duration_ms": audio_duration_ms, "text": "", "words": _words()}

    def fake_render(job_id, audio_path, words_path, props, output_path, log_path, root=None, **kw):
        calls["render"].append(props)
        staged = Path(root or ROOT) / "remotion" / "public" / "jobs" / job_id
        staged.mkdir(parents=True, exist_ok=True)
        (staged / "props.json").write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        Path(log_path).write_text("fake render", encoding="utf-8")
        _make_video(Path(output_path), render.get_audio_duration_ms(audio_path))
        return Path(output_path)

    monkeypatch.setattr(voice, "synthesize", fake_synthesize)
    monkeypatch.setattr(transcript, "transcribe", fake_transcribe)
    monkeypatch.setattr(render, "render_remotion", fake_render)
    return calls


def _run(tmp_path, md_text=None, **cfg):
    md = tmp_path / "in.md"
    md.write_text(md_text if md_text is not None else SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return pipeline.run_job(
        md,
        JobConfig(**cfg),
        jobs_root=tmp_path / "jobs",
        output_path=tmp_path / "output" / "ret.mp4",
        root=tmp_path,
    )


def test_run_job_writes_all_required_artifacts(fake_apis, tmp_path):
    result = _run(tmp_path)
    job_dir = Path(result["job_dir"])
    assert result["status"] == "qc_passed"
    for rel in [
        "inputs/source.md", "inputs/script.md", "inputs/script.json",
        "audio/narration.mp3", "logs/tts_input.txt",
        "transcripts/words.json", "logs/scribe_raw.json",
        "edit/caption_segments.json", "edit/emoticon_cues.json",
        "edit/final.mp4", "logs/remotion.log", "qc_report.json",
    ]:
        assert (job_dir / rel).is_file(), rel
    assert (tmp_path / "remotion" / "public" / "jobs" / result["job_id"] / "props.json").is_file()
    assert (tmp_path / "output" / "ret.mp4").is_file()

    doc = state.read_status(job_dir)
    assert [h["status"] for h in doc["history"]] == [*state.SEQUENCE, "qc_passed"]
    assert doc["config"]["visual_mode"] == "emoticon"
    assert not any(h["status"] in state.PROGRESS_EVENTS for h in doc["history"])


def test_props_and_opening_contract(fake_apis, tmp_path):
    _run(tmp_path)
    props = fake_apis["render"][0]
    assert props["showOpening"] is True
    # 날짜는 음성 없는 배지: 고정 표시 시간, 자막 suppression 없음 (§5.10)
    assert props["openingDurationMs"] == opening.OPENING_BADGE_MS
    assert "데이브리핑" in props["openingText"]
    assert "데이브리핑" not in fake_apis["tts"][0]
    assert props["durationInFrames"] == 180  # 6000ms × 30fps
    assert props["captionSegments"][0]["wordStart"] == 0
    assert props["emoticonCues"][0]["startMs"] == 0
    # numeric_display 가 "삼점이 퍼센트" 를 원문 표시형으로 복원
    words = json.loads(next((tmp_path / "jobs").glob("*/transcripts/words.json")).read_text())["words"]
    assert any("3.2" in w["text"] for w in words)


def test_no_opening_suppression(fake_apis, tmp_path):
    _run(tmp_path, show_opening=False)
    props = fake_apis["render"][0]
    assert props["showOpening"] is False
    assert props["openingDurationMs"] == 0
    assert "데이브리핑" not in fake_apis["tts"][0]


def test_storyboard_job(fake_apis, tmp_path):
    result = _run(tmp_path, STORYBOARD_MD, show_opening=False)
    job_dir = Path(result["job_dir"])
    assert (job_dir / "inputs" / "storyboard.json").is_file()
    assert (job_dir / "edit" / "storyboard_segments.json").is_file()
    script = json.loads((job_dir / "inputs" / "script.json").read_text())
    assert script["plan"]["engine"] == "storyboard"
    assert "화면 연출" not in script["full_text"] and "stock market" not in script["full_text"]
    props = fake_apis["render"][0]
    assert len(props["captionSegments"]) == 2


def test_photo_failure_falls_back_to_emoticon(fake_apis, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(pipeline.script_engine, "generate_script", _no_openai_script(pipeline.script_engine.generate_script))
    events = []

    def boom(*a, on_stage=None, **k):
        assert on_stage is not None
        on_stage("photo_generating")
        raise photo_engine.PhotoEngineError("all prompts moderation_blocked")

    monkeypatch.setattr(photo_engine, "plan_photo_cues", boom)
    md = tmp_path / "in.md"
    md.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    result = pipeline.run_job(md, JobConfig(visual_mode="photo"), jobs_root=tmp_path / "jobs", output_path=None, root=tmp_path, on_stage=events.append)
    job_dir = Path(result["job_dir"])
    assert result["visual_mode"] == "emoticon"
    assert (job_dir / "logs" / "photo_fallback.json").is_file()
    assert (job_dir / "edit" / "emoticon_cues.json").is_file()
    assert not (job_dir / "edit" / "photo_cues.json").exists()
    assert "photo_generating" in events and "photo_fallback" in events
    history = [h["status"] for h in state.read_status(job_dir)["history"]]
    assert not set(history) & state.PROGRESS_EVENTS
    assert state.read_status(job_dir)["visual_mode"] == "emoticon"


def _no_openai_script(real):
    def wrapper(markdown, api_key, **kw):
        return real(markdown, None, **kw)
    return wrapper


def test_photo_success_writes_photo_cues(fake_apis, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(pipeline.script_engine, "generate_script", _no_openai_script(pipeline.script_engine.generate_script))
    cue = {"emoticonFileName": "jobs/x/photos/seg_01_abc.png", "startMs": 0, "durationMs": 1000, "assetKind": "photo", "visualMode": "photo"}
    monkeypatch.setattr(photo_engine, "plan_photo_cues", lambda *a, **k: [cue])
    md = tmp_path / "in.md"
    md.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    result = pipeline.run_job(md, JobConfig(visual_mode="photo"), jobs_root=tmp_path / "jobs", output_path=None, root=tmp_path)
    job_dir = Path(result["job_dir"])
    assert json.loads((job_dir / "edit" / "photo_cues.json").read_text()) == [cue]
    assert not (job_dir / "edit" / "emoticon_cues.json").exists()
    assert fake_apis["render"][0]["emoticonCues"] == [cue]


def test_qc_failure_is_terminal_qc_failed(fake_apis, tmp_path, monkeypatch):
    real_info = render.get_video_info
    monkeypatch.setattr(render, "get_video_info", lambda p: {**real_info(p), "duration_ms": real_info(p)["duration_ms"] + 500})
    result = _run(tmp_path)
    assert result["status"] == "qc_failed"
    assert state.read_status(Path(result["job_dir"]))["status"] == "qc_failed"


def test_exception_marks_failed(fake_apis, tmp_path, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("tts down")

    monkeypatch.setattr(voice, "synthesize", broken)
    with pytest.raises(RuntimeError):
        _run(tmp_path)
    job_dir = next((tmp_path / "jobs").iterdir())
    doc = state.read_status(job_dir)
    assert doc["status"] == "failed"
    assert doc["failed_after"] == "script_generated"
    assert "tts down" in doc["error"]


# --------------------------------------------------------------------------- CLI

runner = CliRunner()


@pytest.fixture
def cli_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.env, "load_env", lambda *a, **k: None)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    md = tmp_path / "in.md"
    md.write_text("# 제목\n\n본문입니다.", encoding="utf-8")
    return md


@pytest.mark.parametrize("args,msg", [
    (["--lang", "en"], "ko"),
    (["--chunk-size", "0"], "chunk-size"),
    (["--chunk-size", "25"], "chunk-size"),
    (["--engine", "ffmpeg"], "remotion"),
    (["--visual-mode", "video"], "visual-mode"),
    (["--speed", "1.5"], "speed"),
    (["--visual-mode", "photo"], "OPENAI_API_KEY"),
    (["--bg", "white"], "--bg"),
])
def test_cli_validation_exit_1(cli_env, args, msg):
    result = runner.invoke(cli.app, ["run", str(cli_env), *args])
    assert result.exit_code == 1, result.output
    assert msg in result.output


def test_cli_missing_elevenlabs_key_exit_1(cli_env, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    result = runner.invoke(cli.app, ["run", str(cli_env)])
    assert result.exit_code == 1
    assert "ELEVENLABS_API_KEY" in result.output


def test_cli_missing_file_exit_1(cli_env):
    assert runner.invoke(cli.app, ["run", "nope.md"]).exit_code == 1


def test_cli_runtime_error_exit_2(cli_env, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("render exploded")

    monkeypatch.setattr(pipeline, "run_job", boom)
    result = runner.invoke(cli.app, ["run", str(cli_env)])
    assert result.exit_code == 2
    assert "render exploded" in result.output


def test_cli_run_success_and_status(cli_env, monkeypatch, tmp_path):
    captured = {}

    def fake_run_job(md, config, **kw):
        captured.update(config=config, **kw)
        job_dir = tmp_path / "jobs" / "sf_20261120_abcdef"
        state.write_status(job_dir, "created", job_id="sf_20261120_abcdef", config=config.model_dump())
        (job_dir / "qc_report.json").write_text(json.dumps({
            "passed": True,
            "checks": [{"name": "final_mp4_vs_audio", "passed": True, "diff_ms": 10, "tolerance_ms": 100}],
            "cost_estimate": {"total_usd": 0.12},
        }))
        return {"job_id": "sf_20261120_abcdef", "status": "qc_passed", "final_mp4": "f.mp4", "output_copy": "output/ret.mp4", "qc_report": "q.json"}

    monkeypatch.setattr(pipeline, "run_job", fake_run_job)
    result = runner.invoke(cli.app, ["run", str(cli_env), "--bg", "#112233", "--chunk-size", "10", "--outro", "-o", ""])
    assert result.exit_code == 0, result.output
    cfg = captured["config"]
    assert cfg.bg_color == "0x112233" and cfg.chunk_size == 10 and cfg.show_outro is True
    assert captured["output_path"] is None

    status = runner.invoke(cli.app, ["status", "sf_20261120_abcdef"])
    assert status.exit_code == 0
    assert "[PASS] final_mp4_vs_audio" in status.output
    assert "0.12" in status.output
    assert runner.invoke(cli.app, ["status", "sf_missing"]).exit_code == 1


def test_cli_qc_failed_exit_2(cli_env, monkeypatch):
    monkeypatch.setattr(pipeline, "run_job", lambda *a, **k: {"job_id": "j", "status": "qc_failed", "final_mp4": "f", "output_copy": None, "qc_report": "q"})
    assert runner.invoke(cli.app, ["run", str(cli_env)]).exit_code == 2


def test_parse_older_than():
    assert cli.parse_older_than("3600") == 3600
    assert cli.parse_older_than("30m") == 1800
    assert cli.parse_older_than("24h") == 86400
    assert cli.parse_older_than("7d") == 604800
    with pytest.raises(ValueError):
        cli.parse_older_than("7w")


def test_cli_clean(cli_env, tmp_path, monkeypatch):
    monkeypatch.setattr(render, "PROJECT_ROOT", tmp_path)
    jobs = tmp_path / "jobs"
    old, new = jobs / "sf_20200101_aaaaaa", jobs / "sf_20261120_bbbbbb"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    staging = tmp_path / "remotion" / "public" / "jobs" / old.name
    staging.mkdir(parents=True)
    os.utime(old, (0, 0))

    dry = runner.invoke(cli.app, ["clean", "--older-than", "7d", "--dry-run"])
    assert dry.exit_code == 0 and "would remove" in dry.output and old.exists()

    real = runner.invoke(cli.app, ["clean", "--older-than", "7d"])
    assert real.exit_code == 0
    assert not old.exists() and not staging.exists() and new.exists()
    assert runner.invoke(cli.app, ["clean", "--older-than", "bad"]).exit_code == 1


@pytest.mark.render
@pytest.mark.skipif(not (ROOT / "remotion" / "node_modules").is_dir(), reason="remotion/node_modules 필요 (cd remotion && npm install)")
def test_pipeline_with_real_remotion_render(monkeypatch, tmp_path):
    """가짜 TTS/Scribe + 실제 Remotion 렌더로 qc_passed 까지."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-eleven")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake_synthesize(text, voice_id, out_path, api_key, speed=1.0, log_dir=None, client=None):
        _make_audio(Path(out_path))
        assert log_dir is not None
        (Path(log_dir) / "tts_input.txt").write_text(text, encoding="utf-8")
        return Path(out_path)

    def fake_transcribe(audio_path, api_key, *, audio_duration_ms, raw_log_path=None, **kw):
        assert raw_log_path is not None
        Path(raw_log_path).write_text("{}", encoding="utf-8")
        return {"language_code": "kor", "audio_duration_ms": audio_duration_ms, "text": "", "words": _words()}

    monkeypatch.setattr(voice, "synthesize", fake_synthesize)
    monkeypatch.setattr(transcript, "transcribe", fake_transcribe)
    md = tmp_path / "in.md"
    md.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    result = pipeline.run_job(md, JobConfig(), jobs_root=tmp_path / "jobs", output_path=tmp_path / "ret.mp4", root=ROOT)
    try:
        assert result["status"] == "qc_passed"
        info = render.get_video_info(Path(result["final_mp4"]))
        assert (info["width"], info["height"]) == (1080, 1920)
        assert abs(info["duration_ms"] - AUDIO_MS) <= 100
        assert (ROOT / "remotion" / "public" / "jobs" / result["job_id"] / "props.json").is_file()
    finally:
        shutil.rmtree(ROOT / "remotion" / "public" / "jobs" / result["job_id"], ignore_errors=True)
