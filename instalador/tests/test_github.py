from subprocess import CompletedProcess
from unittest.mock import MagicMock

from instalador.steps.github import GhError, create_private_repo, get_token, is_authenticated, repo_exists


def _completed(returncode=0, stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_is_authenticated_true():
    run = MagicMock(return_value=_completed(0))
    assert is_authenticated(run=run) is True


def test_is_authenticated_false():
    run = MagicMock(return_value=_completed(1))
    assert is_authenticated(run=run) is False


def test_repo_exists_true():
    run = MagicMock(return_value=_completed(0))
    assert repo_exists("nina-vault", run=run) is True


def test_create_private_repo_skips_if_exists():
    run = MagicMock(return_value=_completed(0))
    create_private_repo("nina-vault", run=run)
    run.assert_called_once_with(["gh", "repo", "view", "nina-vault"], capture_output=True, text=True, check=False)


def test_create_private_repo_creates_if_missing():
    run = MagicMock(side_effect=[_completed(1), _completed(0)])
    create_private_repo("nina-vault", run=run)
    assert run.call_count == 2
    assert run.call_args_list[1].args[0] == ["gh", "repo", "create", "nina-vault", "--private", "--confirm"]


def test_get_token_returns_stripped_output():
    run = MagicMock(return_value=_completed(0, stdout="gho_ABC123\n"))
    assert get_token(run=run) == "gho_ABC123"


def test_get_token_raises_on_failure():
    run = MagicMock(return_value=_completed(1, stderr="not logged in"))
    try:
        get_token(run=run)
        assert False, "deveria ter levantado GhError"
    except GhError:
        pass
