from tuxo import config as config_module

_REQUIRED_ENV = {
    "TELEGRAM_BOT_TOKEN": "t",
    "OWNER_TELEGRAM_CHAT_ID": "1",
    "ANTHROPIC_API_KEY": "a",
    "VAULT_REPO_URL": "https://example.com/x.git",
    "GITHUB_TOKEN": "g",
}


def _set_required_env(monkeypatch):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_bot_name_defaults_to_tuxo(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("BOT_NAME", raising=False)
    config_module.load_config.cache_clear()
    cfg = config_module.load_config()
    assert cfg.bot_name == "Tuxo"


def test_bot_name_from_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("BOT_NAME", "Nina")
    config_module.load_config.cache_clear()
    cfg = config_module.load_config()
    assert cfg.bot_name == "Nina"
