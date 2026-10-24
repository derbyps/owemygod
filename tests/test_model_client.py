from owemygod import model_client


def test_from_env_needs_both(monkeypatch):
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    monkeypatch.setenv("OWEMYGOD_READER_PATH", "tinker://x")
    assert model_client.from_env("OWEMYGOD_READER_PATH") is None


def test_from_env_builds_client(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "k")
    monkeypatch.setenv("OWEMYGOD_WRITER_PATH", "tinker://w")
    c = model_client.from_env("OWEMYGOD_WRITER_PATH")
    assert c.model_path == "tinker://w"
