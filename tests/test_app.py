import yaml
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_openapi_yaml_endpoint() -> None:
    response = client.get("/openapi.yaml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/yaml")

    spec = yaml.safe_load(response.text)
    assert spec["info"]["title"] == "pypo API"
    assert spec["info"]["version"] == "0.1.0"
