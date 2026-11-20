import json
import re
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from md2short import state
from md2short.schema import DEFAULT_VOICES, JobConfig
from md2short.timeutil import frames_to_ms, ms_to_frames, seconds_to_ms


def test_jobconfig_defaults_match_architecture():
    cfg = JobConfig()
    assert cfg.platform == "youtube_shorts"
    assert cfg.language == "ko"
    assert cfg.voice_id == DEFAULT_VOICES["ko"] == "v1jVu1Ky28piIPEJqRrm"
    assert cfg.voice_speed == 1.0
    assert cfg.template_id == "tech_explainer"
    assert cfg.bg_color == "0xFFFFFF"
    assert cfg.chunk_size == 14
    assert cfg.engine == "remotion"
    assert cfg.visual_mode == "emoticon"
    assert cfg.show_opening is True
    assert cfg.show_outro is True


@pytest.mark.parametrize("field,value", [("language", "en"), ("engine", "ffmpeg"), ("chunk_size", 0), ("chunk_size", 25), ("visual_mode", "video")])
def test_jobconfig_rejects_invalid(field, value):
    with pytest.raises(ValidationError):
        JobConfig(**{field: value})


def test_time_helpers():
    assert ms_to_frames(30000) == 900
    assert ms_to_frames(1000) == 30
    assert ms_to_frames(16) == 0
    assert ms_to_frames(17) == 1
    assert frames_to_ms(900) == 30000
    assert seconds_to_ms(1.2346) == 1235
    assert seconds_to_ms(0.32) == 320


def test_full_sequence_allowed():
    cur = None
    for s in [*state.SEQUENCE, "qc_passed"]:
        state.validate_transition(cur, s)
        cur = s


@pytest.mark.parametrize("cur,new", [
    (None, "script_generated"),
    ("created", "voice_generated"),
    ("transcribed", "final_rendered"),
    ("qc_passed", "failed"),
    ("failed", "created"),
    ("subtitled", "qc_passed"),
])
def test_invalid_transitions(cur, new):
    with pytest.raises(ValueError):
        state.validate_transition(cur, new)


@pytest.mark.parametrize("cur", list(state.SEQUENCE))
def test_any_nonterminal_to_failed(cur):
    state.validate_transition(cur, "failed")


@pytest.mark.parametrize("event", sorted(state.PROGRESS_EVENTS))
def test_progress_events_never_status(event):
    with pytest.raises(ValueError):
        state.validate_transition("transcribed", event)


def test_write_status_records_history(tmp_path):
    state.write_status(tmp_path, "created", job_id="sf_x")
    doc = state.write_status(tmp_path, "script_generated")
    on_disk = json.loads((tmp_path / "status.json").read_text())
    assert on_disk["status"] == "script_generated"
    assert [h["status"] for h in on_disk["history"]] == ["created", "script_generated"]
    assert doc["job_id"] == "sf_x"
    with pytest.raises(ValueError):
        state.write_status(tmp_path, "photo_generating")


def test_job_id_format():
    jid = state.new_job_id(datetime(2026, 5, 2, tzinfo=timezone.utc))
    assert re.fullmatch(r"sf_20260502_[0-9a-f]{6}", jid)
