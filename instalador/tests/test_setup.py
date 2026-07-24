from instalador.setup import STEP_ORDER, main
from instalador.state import InstallerState


def test_step_order_has_no_duplicates():
    assert len(STEP_ORDER) == len(set(STEP_ORDER))


def test_dry_run_returns_zero_without_touching_state(tmp_path, monkeypatch, capsys):
    state_path = tmp_path / "estado.json"
    monkeypatch.setattr("instalador.setup.STATE_PATH", state_path)
    exit_code = main(["--dry-run"])
    assert exit_code == 0
    assert not state_path.exists()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out.lower()


def test_resume_skips_completed_steps(tmp_path, monkeypatch):
    state_path = tmp_path / "estado.json"
    monkeypatch.setattr("instalador.setup.STATE_PATH", state_path)
    state = InstallerState()
    for step in STEP_ORDER[:2]:
        state.mark_done(step)
    from instalador.state import save

    save(state, state_path)

    exit_code = main(["--dry-run"])
    assert exit_code == 0
