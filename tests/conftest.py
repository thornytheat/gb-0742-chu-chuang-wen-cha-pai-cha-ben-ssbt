import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.archive.pipeline import evaluate
from app.modules.intake.catalog import load_sample


@pytest.fixture(scope="session")
def package():
    return load_sample("shift")


@pytest.fixture(scope="session")
def snapshot(package):
    return evaluate(package)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "glass.sqlite3", seed=False)) as test:
        yield test


@pytest.fixture
def base(client):
    response = client.post("/api/runs", json={"sample":"shift"})
    assert response.status_code == 201, response.text
    return f'/api/runs/{response.json()["manifest"]["id"]}'
