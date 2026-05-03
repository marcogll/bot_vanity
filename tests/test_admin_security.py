from app.security import (
    generate_csrf_token,
    hash_password,
    issue_admin_session_token,
    read_admin_session_token,
    verify_password,
)


def test_password_hash_verifies_expected_secret() -> None:
    password = "UltraSeguro#2026Panel"
    stored = hash_password(password)

    assert stored.startswith("scrypt$")
    assert verify_password(password, stored)
    assert not verify_password("otro-password", stored)


def test_admin_session_token_round_trip() -> None:
    csrf_token = generate_csrf_token()

    token = issue_admin_session_token(
        user_id="11111111-1111-1111-1111-111111111111",
        csrf_token=csrf_token,
        expires_minutes=5,
    )

    payload = read_admin_session_token(token)

    assert payload is not None
    assert payload["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["csrf"] == csrf_token
