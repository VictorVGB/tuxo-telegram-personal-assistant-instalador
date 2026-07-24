from instalador.state import InstallerState, load, save


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "estado.json"
    state = InstallerState()
    state.data.bot_name = "Nina"
    state.mark_done("bot_identity")
    save(state, path)

    loaded = load(path)
    assert loaded.data.bot_name == "Nina"
    assert loaded.is_done("bot_identity") is True
    assert loaded.is_done("telegram") is False


def test_load_missing_file_returns_fresh_state(tmp_path):
    path = tmp_path / "nao-existe.json"
    state = load(path)
    assert state.completed_steps == []
    assert state.data.bot_name == ""


def test_mark_done_is_idempotent():
    state = InstallerState()
    state.mark_done("prereqs")
    state.mark_done("prereqs")
    assert state.completed_steps == ["prereqs"]
