from subprocess import CompletedProcess

from instalador.steps.prereqs import all_ok, check_tools


def _fake_run(stdout='{"terraform_version": "1.10.2"}'):
    def run(args, **kwargs):
        return CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")
    return run


def test_check_tools_all_found():
    checks = check_tools("linux", which=lambda name: f"/usr/bin/{name}", run=_fake_run())
    assert all_ok(checks) is True
    assert len(checks) == 5


def test_check_tools_missing_tool():
    def fake_which(name):
        return None if name == "docker" else f"/usr/bin/{name}"

    checks = check_tools("linux", which=fake_which, run=_fake_run())
    assert all_ok(checks) is False
    docker_check = next(c for c in checks if c.name == "docker")
    assert docker_check.found is False
    assert docker_check.install_url == "https://docs.docker.com/desktop/install/linux/"


def test_check_tools_old_terraform_version():
    checks = check_tools(
        "linux", which=lambda name: f"/usr/bin/{name}", run=_fake_run('{"terraform_version": "1.6.0"}')
    )
    assert all_ok(checks) is False
    tf_check = next(c for c in checks if c.name == "terraform")
    assert tf_check.version_ok is False
