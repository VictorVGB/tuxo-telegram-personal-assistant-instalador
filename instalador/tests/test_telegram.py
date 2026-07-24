import httpx

from instalador.steps.telegram import discover_chat_id, validate_bot_token


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_validate_bot_token_ok():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": {"id": 123}})

    assert validate_bot_token("FAKE:TOKEN", client=_client(handler)) is True


def test_validate_bot_token_invalid():
    def handler(request):
        return httpx.Response(401, json={"ok": False})

    assert validate_bot_token("FAKE:TOKEN", client=_client(handler)) is False


def test_discover_chat_id_found():
    def handler(request):
        return httpx.Response(
            200, json={"ok": True, "result": [{"update_id": 1, "message": {"chat": {"id": 555}}}]}
        )

    assert discover_chat_id("FAKE:TOKEN", client=_client(handler)) == "555"


def test_discover_chat_id_no_messages():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": []})

    assert discover_chat_id("FAKE:TOKEN", client=_client(handler)) is None
