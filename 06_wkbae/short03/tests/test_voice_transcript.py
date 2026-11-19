import json

import httpx
import pytest

from md2short.env import MissingEnvError
from md2short.transcript import transcribe
from md2short.voice import synthesize


def test_synthesize_request_shape(tmp_path):
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = req.url
        seen["headers"] = req.headers
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, content=b"MP3DATA")

    out = synthesize(
        "안녕하세요.", "VOICE1", tmp_path / "audio" / "narration.mp3", "key123", speed=1.1,
        log_dir=tmp_path / "logs", client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert out.read_bytes() == b"MP3DATA"
    assert seen["url"].path == "/v1/text-to-speech/VOICE1"
    assert seen["url"].params["output_format"] == "mp3_44100_128"
    assert seen["headers"]["xi-api-key"] == "key123"
    assert seen["body"]["model_id"] == "eleven_multilingual_v2"
    assert seen["body"]["voice_settings"]["speed"] == 1.1
    assert seen["body"]["text"] == "안녕하세요."
    assert (tmp_path / "logs" / "tts_input.txt").read_text(encoding="utf-8") == "안녕하세요."


def test_synthesize_missing_key(tmp_path):
    with pytest.raises(MissingEnvError, match="ELEVENLABS_API_KEY"):
        synthesize("a", "v", tmp_path / "a.mp3", None)


def test_transcribe_shape_rounding_filter_and_raw_log(tmp_path):
    audio = tmp_path / "narration.mp3"
    audio.write_bytes(b"AUDIO")
    seen = {}
    raw = {
        "language_code": "kor",
        "text": "금일 미국",
        "words": [
            {"text": "금일", "start": 0.0, "end": 0.3204, "type": "word"},
            {"text": " ", "start": 0.3204, "end": 0.33, "type": "spacing"},
            {"text": "미국", "start": 0.3306, "end": 0.5905, "type": "word"},
            {"text": "(웃음)", "start": 0.6, "end": 0.9, "type": "audio_event"},
        ],
    }

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["ct"] = req.headers["content-type"]
        seen["body"] = req.content
        seen["key"] = req.headers["xi-api-key"]
        return httpx.Response(200, json=raw)

    doc = transcribe(
        audio, "k", audio_duration_ms=30000, language="ko",
        out_path=tmp_path / "transcripts" / "words.json",
        raw_log_path=tmp_path / "logs" / "scribe_raw.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert seen["url"] == "https://api.elevenlabs.io/v1/speech-to-text"
    assert seen["ct"].startswith("multipart/form-data")
    body = seen["body"].decode("utf-8", "ignore")
    assert 'name="model_id"' in body and "scribe_v1" in body
    assert 'name="language_code"' in body and "kor" in body
    assert "timestamps_granularity" in body and "word" in body
    assert 'name="file"' in body and "AUDIO" in body
    assert seen["key"] == "k"
    assert doc == {
        "language_code": "kor",
        "audio_duration_ms": 30000,
        "text": "금일 미국",
        "words": [
            {"text": "금일", "start": 0, "end": 320},
            {"text": "미국", "start": 331, "end": 590},
        ],
    }
    assert json.loads((tmp_path / "transcripts" / "words.json").read_text(encoding="utf-8")) == doc
    assert json.loads((tmp_path / "logs" / "scribe_raw.json").read_text(encoding="utf-8")) == raw


def test_transcribe_rejects_non_ko_and_missing_key(tmp_path):
    a = tmp_path / "a.mp3"
    a.write_bytes(b"x")
    with pytest.raises(ValueError):
        transcribe(a, "k", audio_duration_ms=1, language="en")
    with pytest.raises(MissingEnvError):
        transcribe(a, None, audio_duration_ms=1)
