"""md2short.render 테스트 (architecture.md §2.3, §4.3, §5.5)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from md2short import render
from md2short.timeutil import ms_to_frames

REPO_ROOT = Path(__file__).resolve().parent.parent

PROPS_KEYS = [
    "audioFileName",
    "wordsFileName",
    "bgColor",
    "chunkSize",
    "emoticonCues",
    "captionSegments",
    "companyLogoCues",
    "numberCards",
    "highlightKeywords",
    "openingText",
    "openingDurationMs",
    "showOpening",
    "ctaText",
    "showOutro",
    "durationInFrames",
]


# --------------------------------------------------------------------------- props


def test_build_props_has_exact_schema_keys():
    props = render.build_props("sf_20261120_abc123", 30000)
    assert list(props.keys()) == PROPS_KEYS


def test_build_props_paths_and_defaults():
    props = render.build_props("sf_20261120_abc123", 30000)
    assert props["audioFileName"] == "jobs/sf_20261120_abc123/narration.mp3"
    assert props["wordsFileName"] == "jobs/sf_20261120_abc123/words.json"
    assert props["bgColor"] == "#FFFFFF"
    assert props["chunkSize"] == 14
    assert props["showOutro"] is False
    assert props["ctaText"] == "🐯 구독 + 알람"


@pytest.mark.parametrize(
    ("audio_ms", "frames"),
    [(30000, 900), (4000, 120), (12345, 370), (16, 1), (0, 1)],
)
def test_build_props_duration_from_audio(audio_ms, frames):
    props = render.build_props("sf_20261120_abc123", audio_ms)
    assert props["durationInFrames"] == frames
    if audio_ms >= 17:
        assert props["durationInFrames"] == ms_to_frames(audio_ms)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0xFFFFFF", "#FFFFFF"),
        ("0x1a2b3c", "#1A2B3C"),
        ("#00ff00", "#00FF00"),
        ("ABCDEF", "#ABCDEF"),
        ("0xfff", "#FFF"),
    ],
)
def test_normalize_bg_color(raw, expected):
    assert render.normalize_bg_color(raw) == expected
    assert render.build_props("sf_x", 1000, bg_color=raw)["bgColor"] == expected


@pytest.mark.parametrize("bad", ["white", "0xGGGGGG", "#12345", ""])
def test_normalize_bg_color_rejects_invalid(bad):
    with pytest.raises(ValueError):
        render.normalize_bg_color(bad)


def test_build_props_opening_contract():
    on = render.build_props(
        "sf_x", 10000, opening_text="2026년 11월 20일\n데이브리핑", opening_duration_ms=2800, show_opening=True
    )
    assert on["showOpening"] is True
    assert on["openingDurationMs"] == 2800
    assert on["openingText"] == "2026년 11월 20일\n데이브리핑"

    off = render.build_props(
        "sf_x", 10000, opening_text="2026년 11월 20일\n데이브리핑", opening_duration_ms=2800, show_opening=False
    )
    assert off["showOpening"] is False
    assert off["openingDurationMs"] == 0  # §5.10 suppression 0ms


def test_build_props_passes_cues_through():
    cue = {"emoticonFileName": "emoticon/09_가즈아_상승.png", "startMs": 0, "durationMs": 1000,
           "assetKind": "emoticon", "visualMode": "emoticon"}
    props = render.build_props(
        "sf_x",
        5000,
        chunk_size=20,
        emoticon_cues=[cue],
        number_cards=[{"text": "5%", "startMs": 100, "durationMs": 1800}],
        company_logo_cues=[{"logoFileName": "company/apple.png", "name": "Apple", "startMs": 0, "durationMs": 1800}],
        caption_segments=[{"index": 0, "startMs": 0, "endMs": 900, "text": "오늘", "wordStart": 0, "wordEnd": 1}],
        highlight_keywords=["애플"],
    )
    assert props["emoticonCues"] == [cue]
    assert props["chunkSize"] == 20
    assert props["numberCards"][0]["text"] == "5%"
    assert props["companyLogoCues"][0]["logoFileName"] == "company/apple.png"
    assert props["captionSegments"][0]["wordEnd"] == 1
    assert props["highlightKeywords"] == ["애플"]


# --------------------------------------------------------------------------- staging


def _fake_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for name in render.SHARED_ASSET_DIRS:
        (root / name).mkdir(parents=True)
        (root / name / f"{name}.txt").write_text(name)
    (root / "remotion" / "public").mkdir(parents=True)
    (root / "remotion" / "node_modules").mkdir()
    return root


def test_stage_assets_paths(tmp_path):
    root = _fake_root(tmp_path)
    audio = tmp_path / "a.mp3"
    words = tmp_path / "w.json"
    audio.write_bytes(b"ID3fake")
    words.write_text('{"words": []}')

    staged = render.stage_assets("sf_20261120_abc123", audio, words, root)

    job_dir = root / "remotion" / "public" / "jobs" / "sf_20261120_abc123"
    assert staged["job_dir"] == job_dir
    assert (job_dir / "narration.mp3").read_bytes() == b"ID3fake"
    assert (job_dir / "words.json").read_text() == '{"words": []}'
    for name in render.SHARED_ASSET_DIRS:
        link = root / "remotion" / "public" / name
        assert (link / f"{name}.txt").read_text() == name
        if link.is_symlink():
            assert link.readlink() == Path(f"../../{name}")

    # idempotent
    render.stage_assets("sf_20261120_abc123", audio, words, root)


def test_stage_assets_copy_fallback(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    audio = tmp_path / "a.mp3"
    words = tmp_path / "w.json"
    audio.write_bytes(b"x")
    words.write_text("{}")

    def no_symlink(self, *args, **kwargs):
        raise OSError("symlinks not supported")

    monkeypatch.setattr(Path, "symlink_to", no_symlink)
    render.stage_assets("sf_x", audio, words, root)
    for name in render.SHARED_ASSET_DIRS:
        link = root / "remotion" / "public" / name
        assert link.is_dir() and not link.is_symlink()
        assert (link / f"{name}.txt").read_text() == name


def test_stage_assets_missing_asset_dir(tmp_path):
    root = _fake_root(tmp_path)
    shutil.rmtree(root / "company")
    audio = tmp_path / "a.mp3"
    words = tmp_path / "w.json"
    audio.write_bytes(b"x")
    words.write_text("{}")
    with pytest.raises(RuntimeError, match="company"):
        render.stage_assets("sf_x", audio, words, root)


# --------------------------------------------------------------------------- pre-flight


def test_ensure_ffmpeg_available_missing(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda tool: None if tool == "ffprobe" else "/bin/x")
    with pytest.raises(RuntimeError, match="ffprobe"):
        render.ensure_ffmpeg_available()


def test_ensure_remotion_available(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="Remotion 프로젝트"):
        render.ensure_remotion_available(tmp_path)
    (tmp_path / "remotion").mkdir()
    with pytest.raises(RuntimeError, match="npm install"):
        render.ensure_remotion_available(tmp_path)
    (tmp_path / "remotion" / "node_modules").mkdir()
    monkeypatch.setattr(render.shutil, "which", lambda tool: None)
    with pytest.raises(RuntimeError, match="npx"):
        render.ensure_remotion_available(tmp_path)
    monkeypatch.setattr(render.shutil, "which", lambda tool: "/usr/bin/npx")
    render.ensure_remotion_available(tmp_path)


# --------------------------------------------------------------------------- command


def test_build_render_command_exact():
    cmd = render.build_render_command("/abs/out.mp4", "/abs/props.json")
    assert cmd == [
        "npx", "remotion", "render", "src/index.ts", "TechExplainer", "/abs/out.mp4",
        "--props=/abs/props.json", "--codec=h264", "--audio-bitrate=192k", "--width=1080", "--height=1920",
        "--log=warn", "--overwrite",
    ]


def _mock_inputs(tmp_path):
    root = _fake_root(tmp_path)
    audio = tmp_path / "a.mp3"
    words = tmp_path / "w.json"
    audio.write_bytes(b"x")
    words.write_text("{}")
    return root, audio, words


def test_render_remotion_runs_command_and_writes_props(tmp_path, monkeypatch):
    root, audio, words = _mock_inputs(tmp_path)
    calls = {}

    def fake_run(cmd, cwd=None, capture_output=None, text=None, timeout=None):
        calls.update(cmd=cmd, cwd=cwd, timeout=timeout)
        Path(cmd[5]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok out", stderr="")

    monkeypatch.setattr(render.shutil, "which", lambda tool: "/usr/bin/" + tool)
    monkeypatch.setattr(render, "get_audio_duration_ms", lambda p: 4000)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    props = render.build_props("sf_x", 1, bg_color="0x000000")
    out = tmp_path / "job" / "edit" / "final.mp4"
    log = tmp_path / "job" / "logs" / "remotion.log"
    result = render.render_remotion("sf_x", audio, words, props, out, log, root=root, timeout_s=77)

    props_path = root / "remotion" / "public" / "jobs" / "sf_x" / "props.json"
    assert result == out.resolve()
    assert calls["cwd"] == root / "remotion"
    assert calls["timeout"] == 77
    assert calls["cmd"] == render.build_render_command(out.resolve(), props_path.resolve())
    written = json.loads(props_path.read_text(encoding="utf-8"))
    assert list(written.keys()) == PROPS_KEYS
    assert written["durationInFrames"] == 120  # from measured audio, not caller value
    assert written["bgColor"] == "#000000"
    assert "ok out" in log.read_text(encoding="utf-8")


def test_render_remotion_failure_raises_with_log_tail(tmp_path, monkeypatch):
    root, audio, words = _mock_inputs(tmp_path)
    monkeypatch.setattr(render.shutil, "which", lambda tool: "/usr/bin/" + tool)
    monkeypatch.setattr(render, "get_audio_duration_ms", lambda p: 1000)
    monkeypatch.setattr(
        render.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom: composition crashed"),
    )
    log = tmp_path / "remotion.log"
    with pytest.raises(RuntimeError, match="boom: composition crashed"):
        render.render_remotion("sf_x", audio, words, render.build_props("sf_x", 1000),
                               tmp_path / "o.mp4", log, root=root)
    assert "exit 1" in log.read_text(encoding="utf-8")


def test_render_remotion_timeout(tmp_path, monkeypatch):
    root, audio, words = _mock_inputs(tmp_path)
    monkeypatch.setattr(render.shutil, "which", lambda tool: "/usr/bin/" + tool)
    monkeypatch.setattr(render, "get_audio_duration_ms", lambda p: 1000)

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"], output=b"partial", stderr=b"still rendering")

    monkeypatch.setattr(render.subprocess, "run", slow)
    log = tmp_path / "remotion.log"
    with pytest.raises(RuntimeError, match="시간 초과"):
        render.render_remotion("sf_x", audio, words, render.build_props("sf_x", 1000),
                               tmp_path / "o.mp4", log, root=root, timeout_s=5)
    assert "still rendering" in log.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- layer guard


FORBIDDEN = re.compile(r"subtitles=|overlay=|drawtext|\]overlay\b|\boverlay\[")


def test_no_ffmpeg_subtitle_or_overlay_paths():
    """AGENTS.md §3.4: 자막·오버레이는 Remotion 단독. ffmpeg 자막/overlay 필터 금지."""
    files = list((REPO_ROOT / "md2short").rglob("*.py")) + [
        p for p in (REPO_ROOT / "remotion" / "src").rglob("*") if p.suffix in {".ts", ".tsx"}
    ]
    assert files
    hits = [
        f"{p.relative_to(REPO_ROOT)}:{n}: {line.strip()}"
        for p in files
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if FORBIDDEN.search(line)
    ]
    assert hits == []


def test_remotion_frame_conversion_single_helper():
    """AGENTS.md §4.2: TSX 의 ms→frame 변환은 src/time.ts 한 곳에서만."""
    inline = re.compile(r"\*\s*fps\s*\)?\s*/\s*1000|/\s*1000\s*\)?\s*\*\s*fps")
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for p in (REPO_ROOT / "remotion" / "src").rglob("*.ts*")
        if p.name != "time.ts" and inline.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# --------------------------------------------------------------------------- real render smoke


requires_remotion = pytest.mark.skipif(
    not (REPO_ROOT / "remotion" / "node_modules").is_dir()
    or shutil.which("ffmpeg") is None
    or shutil.which("npx") is None,
    reason="remotion/node_modules, ffmpeg, npx 필요",
)


@pytest.mark.render
@requires_remotion
def test_render_remotion_smoke(tmp_path):
    job_id = "sf_20261120_test01"
    audio = tmp_path / "narration.mp3"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=4", "-c:a", "libmp3lame", "-b:a", "128k", str(audio)],
        check=True,
        timeout=60,
    )
    audio_ms = render.get_audio_duration_ms(audio)
    words = tmp_path / "words.json"
    words.write_text(
        json.dumps(
            {
                "language_code": "kor",
                "audio_duration_ms": audio_ms,
                "text": "오늘 애플 주가가 5% 상승했습니다. 반도체도 강세입니다.",
                "words": [
                    {"text": "오늘", "start": 100, "end": 400},
                    {"text": "애플", "start": 450, "end": 800},
                    {"text": "주가가", "start": 850, "end": 1300},
                    {"text": "5%", "start": 1350, "end": 1700},
                    {"text": "상승했습니다.", "start": 1750, "end": 2300},
                    {"text": "반도체도", "start": 2500, "end": 2900},
                    {"text": "강세입니다.", "start": 2950, "end": 3700},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    props = render.build_props(
        job_id,
        audio_ms,
        emoticon_cues=[
            {"emoticonFileName": "emoticon/09_가즈아_상승.png", "startMs": 0, "durationMs": audio_ms,
             "keyword": "상승", "assetKind": "emoticon", "visualMode": "emoticon"}
        ],
        number_cards=[{"text": "+5%", "startMs": 1300, "durationMs": 1800}],
        company_logo_cues=[{"logoFileName": "company/apple.png", "name": "Apple", "startMs": 400, "durationMs": 1800}],
        highlight_keywords=["애플", "반도체"],
        show_opening=False,
    )
    out = tmp_path / "edit" / "final.mp4"
    log = tmp_path / "logs" / "remotion.log"
    try:
        result = render.render_remotion(job_id, audio, words, props, out, log, root=REPO_ROOT)
        info = render.get_video_info(result)
        assert (info["width"], info["height"]) == (1080, 1920)
        assert abs(info["duration_ms"] - audio_ms) <= 100
        assert (render.public_job_dir(job_id, REPO_ROOT) / "props.json").is_file()
        assert log.is_file()
    finally:
        shutil.rmtree(render.public_job_dir(job_id, REPO_ROOT), ignore_errors=True)
