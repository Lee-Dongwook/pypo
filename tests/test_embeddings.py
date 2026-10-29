from src.app.shared.embeddings import Embedding, embedding_endpoint


def test_without_binding_host_there_is_no_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_BINDING_HOST", raising=False)

    assert embedding_endpoint("text-embedding-3-small") is None


def test_binding_host_builds_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_BINDING_HOST", "http://localhost:8080/v1")
    monkeypatch.setenv("EMBEDDING_BINDING_API_KEY", "sk-test")

    endpoint = embedding_endpoint("text-embedding-3-small")

    assert endpoint is not None
    assert endpoint.base_url == "http://localhost:8080/v1"
    assert endpoint.embedding_model_name == "text-embedding-3-small"
    assert endpoint.is_binding is True
    assert endpoint.client_key() == "sk-test"


def test_binding_without_key_falls_back_to_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_BINDING_HOST", "http://localhost:8080/v1")
    monkeypatch.delenv("EMBEDDING_BINDING_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    endpoint = embedding_endpoint("text-embedding-3-small")

    assert endpoint is not None
    assert endpoint.client_key() == "sk-env"


def test_unbound_endpoint_uses_dummy_key() -> None:
    endpoint = Embedding(
        base_url="http://localhost:8080/v1",
        api_key=None,
        is_binding=False,
        embedding_model_name="text-embedding-3-small",
    )

    assert endpoint.client_key() == "dummy"
