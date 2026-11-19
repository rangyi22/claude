import json

import pytest

from md2short import qc


def _run(tmp_path, audio_ms, video_ms, last_end, words=True):
    words_doc = {"words": [{"text": "끝", "start": 0, "end": last_end}] if words else []}
    return qc.run_qc(
        job_dir=tmp_path,
        audio_path=tmp_path / "a.mp3",
        final_mp4=tmp_path / "f.mp4",
        words_doc=words_doc,
        cost_inputs={"tts_chars": 1000, "openai_input_chars": 4000, "openai_output_chars": 4000},
        audio_duration_fn=lambda _p: audio_ms,
        video_info_fn=lambda _p: {"duration_ms": video_ms, "width": 1080, "height": 1920},
    )


def test_pass_within_tolerances(tmp_path):
    report = _run(tmp_path, 30000, 30100, 29000)
    assert report["passed"] is True
    on_disk = json.loads((tmp_path / "qc_report.json").read_text())
    assert [c["name"] for c in on_disk["checks"]] == ["sync_last_word_vs_audio", "final_mp4_vs_audio"]
    assert on_disk["duration_policy"]["source"] == "tts_audio_duration"


@pytest.mark.parametrize("video_ms,last_end", [(30101, 29500), (29899, 29500), (30000, 28999)])
def test_fail_outside_tolerances(tmp_path, video_ms, last_end):
    assert _run(tmp_path, 30000, video_ms, last_end)["passed"] is False


def test_fail_without_words(tmp_path):
    assert _run(tmp_path, 30000, 30000, 0, words=False)["passed"] is False


def test_cost_estimate_formula():
    cost = qc.estimate_cost(tts_chars=1000, audio_duration_ms=3_600_000, openai_input_chars=4_000_000, openai_output_chars=4_000_000)
    assert cost["elevenlabs_tts_usd"] == pytest.approx(0.30)
    assert cost["elevenlabs_stt_usd"] == pytest.approx(0.40)
    assert cost["openai_text_usd"] == pytest.approx(qc.OPENAI_GPT55_INPUT_USD_PER_1M + qc.OPENAI_GPT55_OUTPUT_USD_PER_1M)
    assert cost["total_usd"] == pytest.approx(0.70 + cost["openai_text_usd"])
