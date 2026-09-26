import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root():

    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "电影资料查询系统"
    }


def test_movies_page():

    response = client.get(
        "/movies?page=1&page_size=3"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 3
    assert "total" in data
    assert isinstance(
        data["items"],
        list,
    )


def test_invalid_page():

    response = client.get(
        "/movies?page=0"
    )

    assert response.status_code == 422