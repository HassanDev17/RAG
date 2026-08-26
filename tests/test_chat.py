from app.api.v1 import chat as chat_route


def test_chat_returns_llm_reply(client, monkeypatch):
    monkeypatch.setattr(
        chat_route, "handle_chat", lambda message: chat_route.ChatResponse(role="assistant", content="AI is...")
    )

    response = client.post("/api/v1/chat", json={"role": "user", "content": "What is AI"})

    assert response.status_code == 200
    assert response.json() == {"role": "assistant", "content": "AI is..."}
