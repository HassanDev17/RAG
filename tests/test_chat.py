def test_chat_echoes_message(client):
    payload = {"role": "user", "content": "What is AI"}

    response = client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == payload
