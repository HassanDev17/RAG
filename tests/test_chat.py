from app.api.v1 import chat as chat_route


def test_chat_returns_llm_reply(client, monkeypatch):
    monkeypatch.setattr(
        chat_route,
        "handle_chat",
        lambda message: chat_route.ChatResponse(role="assistant", content="AI is...", latency_ms=12.3),
    )

    response = client.post("/api/v1/chat", json={"role": "user", "content": "What is AI"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["content"] == "AI is..."
    assert body["latency_ms"] == 12.3
