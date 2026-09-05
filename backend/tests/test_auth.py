def test_signup_and_login(client):
    resp = client.post("/auth/signup", json={"email": "a@example.com", "password": "secret123"})
    assert resp.status_code == 201
    assert "access_token" in resp.json()

    resp = client.post(
        "/auth/login",
        data={"username": "a@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_signup_duplicate_email_rejected(client):
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "secret123"})
    resp = client.post("/auth/signup", json={"email": "dup@example.com", "password": "other456"})
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/auth/signup", json={"email": "b@example.com", "password": "secret123"})
    resp = client.post("/auth/login", data={"username": "b@example.com", "password": "wrong"})
    assert resp.status_code == 401
