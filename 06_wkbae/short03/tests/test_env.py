import pytest

from md2short.env import MissingEnvError, get_openai_key, load_env, require_elevenlabs_key


def test_missing_elevenlabs_key_raises(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(MissingEnvError, match="ELEVENLABS_API_KEY"):
        require_elevenlabs_key()


def test_key_returned_and_not_in_error(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "  sk-secret  ")
    assert require_elevenlabs_key() == "sk-secret"


def test_openai_key_optional(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_openai_key() is None
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert get_openai_key() == "k"


def test_load_env_reads_dotenv_without_override(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("ELEVENLABS_API_KEY=from_file\nOPENAI_API_KEY=file_openai\n")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "already")
    load_env(f)
    assert require_elevenlabs_key() == "from_file"
    assert get_openai_key() == "already"
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
