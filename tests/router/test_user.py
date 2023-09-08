def test_register(register_user):
    pass


def test_login(login_cookie):
    pass


def test_me(client, login_cookie):
    resp = client.get("/api/user/me", headers={"access_token_cookie": login_cookie})
    assert resp.json() == {"username": "test"}


def test_logout(client, login_cookie):
    resp = client.post(
        "/api/user/logout", headers={"access_token_cookie": login_cookie}
    )
    assert resp.cookies.get("access_token_cookie") == '""'
    assert resp.text == "user logged out"
