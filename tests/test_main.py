import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import database


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    original_database_file = database.DATABASE_FILE
    database.DATABASE_FILE = tmp_path_factory.mktemp("movies") / "movies.db"
    try:
        from main import app
        with TestClient(app) as test_client:
            yield test_client
    finally:
        database.DATABASE_FILE = original_database_file


def test_root(client):

    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "电影资料查询系统"
    }


def test_movies_page(client):

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


def test_invalid_page(client):

    response = client.get(
        "/movies?page=0"
    )

    assert response.status_code == 422


def test_tool_user_id_is_injected(client, monkeypatch):
    import movie_agent

    captured = {}

    def fake_update_user_memory(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setitem(
        movie_agent.tool_registry["update_user_memory"],
        "function",
        fake_update_user_memory,
    )
    result = movie_agent.execute_tool(
        "update_user_memory",
        '{"user_id": "model-chosen", "favorite_type": "科幻"}',
        user_id="request-user",
    )

    assert result["success"] is True
    assert captured["user_id"] == "request-user"


def test_stream_has_done_event(client, monkeypatch):
    import langgraph_movie_agent

    def fake_stream(*args, **kwargs):
        yield "custom", {"type": "token", "content": "你好"}

    monkeypatch.setattr(langgraph_movie_agent.movie_graph, "stream", fake_stream)
    lines = list(langgraph_movie_agent.stream_movie_agent("问候", "s1", "u1"))

    assert [json.loads(line)["type"] for line in lines] == ["token", "done"]
    assert all(line.endswith("\n") for line in lines)


def test_stream_reports_failure(client, monkeypatch):
    import langgraph_movie_agent

    def failing_stream(*args, **kwargs):
        raise RuntimeError("simulated upstream failure")
        yield  # Keep this a generator, like the real graph stream.

    monkeypatch.setattr(langgraph_movie_agent.movie_graph, "stream", failing_stream)
    lines = list(langgraph_movie_agent.stream_movie_agent("问候", "s2", "u1"))

    assert [json.loads(line)["type"] for line in lines] == ["error"]
