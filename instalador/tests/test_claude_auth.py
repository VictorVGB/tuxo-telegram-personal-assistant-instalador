from unittest.mock import MagicMock

from instalador.steps.claude_auth import ClaudeAuthError, validate_api_key


def _client_returning(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock(status_code=status_code, text=text)
    client = MagicMock()
    client.post.return_value = resp
    return client


def test_validate_api_key_rejects_wrong_prefix():
    try:
        validate_api_key("sk-ant-oat01-abc", client=MagicMock())
        assert False, "deveria ter levantado ClaudeAuthError"
    except ClaudeAuthError as e:
        assert "não parece uma API key" in str(e)


def test_validate_api_key_accepts_valid_key():
    client = _client_returning(200)
    validate_api_key("sk-ant-api03-valid", client=client)
    client.post.assert_called_once()


def test_validate_api_key_accepts_rate_limited_key():
    """429 ainda prova que a key autenticou — não é motivo de erro."""
    client = _client_returning(429)
    validate_api_key("sk-ant-api03-valid", client=client)


def test_validate_api_key_raises_on_401():
    client = _client_returning(401)
    try:
        validate_api_key("sk-ant-api03-invalid", client=client)
        assert False, "deveria ter levantado ClaudeAuthError"
    except ClaudeAuthError as e:
        assert "401" in str(e)


def test_validate_api_key_raises_on_unexpected_error():
    client = _client_returning(500, text="internal error")
    try:
        validate_api_key("sk-ant-api03-valid", client=client)
        assert False, "deveria ter levantado ClaudeAuthError"
    except ClaudeAuthError as e:
        assert "500" in str(e)
