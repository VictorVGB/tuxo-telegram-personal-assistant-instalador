import pytest

from instalador.state import InstallerData
from instalador.steps.write_config import (
    render_backend_hcl,
    render_env_local,
    render_resumo,
    render_tfvars,
    write_all,
    write_resumo,
)


def _sample_data() -> InstallerData:
    return InstallerData(
        bot_name="Nina",
        project_name="nina",
        telegram_bot_token="123:ABC",
        owner_telegram_chat_id="999",
        github_token="gho_xyz",
        vault_repo_url="https://github.com/exemplo/nina-vault.git",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        alert_email="nina@exemplo.com",
        budget_limit_usd=10,
        anthropic_api_key="sk-ant-api03-xyz",
        tf_state_bucket="nina-terraform-state-123456789012",
    )


def test_render_backend_hcl():
    assert render_backend_hcl("nina-terraform-state-123456789012", "us-east-1") == (
        'bucket = "nina-terraform-state-123456789012"\n'
        'region = "us-east-1"\n'
    )


def test_render_tfvars_contains_all_fields():
    content = render_tfvars(_sample_data())
    assert 'project_name = "nina"' in content
    assert 'bot_name = "Nina"' in content
    assert 'telegram_bot_token = "123:ABC"' in content
    assert 'budget_limit_usd = 10' in content


def test_render_env_local_contains_bot_name():
    content = render_env_local(_sample_data())
    assert "BOT_NAME=Nina" in content
    assert "TELEGRAM_BOT_TOKEN=123:ABC" in content


def test_write_all_creates_files(tmp_path):
    infra_dir = tmp_path / "infra"
    infra_dir.mkdir()
    env_local_path = tmp_path / ".env.local"
    write_all(_sample_data(), infra_dir, env_local_path)
    assert (infra_dir / "backend.hcl").exists()
    assert (infra_dir / "terraform.tfvars").exists()
    assert env_local_path.exists()


def test_render_resumo_contains_key_facts():
    content = render_resumo(
        _sample_data(),
        ecr_url="123.dkr.ecr.us-east-1.amazonaws.com/nina-bot",
        ecs_cluster="nina",
        ecs_service="nina",
    )
    assert "Nina" in content
    assert "nina-vault" in content
    assert "123.dkr.ecr.us-east-1.amazonaws.com/nina-bot" in content


def test_write_resumo_creates_file(tmp_path):
    resumo_path = tmp_path / "RESUMO.md"
    write_resumo(
        _sample_data(),
        resumo_path,
        ecr_url="123.dkr.ecr.us-east-1.amazonaws.com/nina-bot",
        ecs_cluster="nina",
        ecs_service="nina",
    )
    assert resumo_path.exists()


# New tests for escaping and newline rejection
def test_render_tfvars_escapes_quotes():
    """Test that double quotes in field values are properly escaped in HCL output."""
    data = _sample_data()
    data.bot_name = 'Nina "A" Silva'
    content = render_tfvars(data)
    # The line should contain escaped quotes: \"A\"
    assert 'bot_name = "Nina \\"A\\" Silva"' in content


def test_render_tfvars_escapes_backslashes():
    """Test that backslashes in field values are properly escaped in HCL output."""
    data = _sample_data()
    data.alert_email = r"test\user@example.com"
    content = render_tfvars(data)
    # Backslash should be escaped
    assert r'alert_email = "test\\user@example.com"' in content


def test_render_backend_hcl_escapes_quotes():
    """Test that double quotes in bucket name are properly escaped in HCL output."""
    content = render_backend_hcl('bucket"with"quotes', "us-east-1")
    assert 'bucket = "bucket\\"with\\"quotes"' in content


def test_render_tfvars_rejects_newline_in_bot_name():
    """Test that newlines in field values raise ValueError."""
    data = _sample_data()
    data.bot_name = "Nina\nEvilLine"
    with pytest.raises(ValueError, match="quebra de linha"):
        render_tfvars(data)


def test_render_tfvars_rejects_carriage_return_in_email():
    """Test that carriage returns in field values raise ValueError."""
    data = _sample_data()
    data.alert_email = "test@example.com\rEvilLine"
    with pytest.raises(ValueError, match="quebra de linha"):
        render_tfvars(data)


def test_render_backend_hcl_rejects_newline():
    """Test that newlines in bucket name raise ValueError."""
    with pytest.raises(ValueError, match="quebra de linha"):
        render_backend_hcl("bucket\nwith\nnewline", "us-east-1")


def test_render_env_local_rejects_newline():
    """Test that newlines in env values raise ValueError."""
    data = _sample_data()
    data.bot_name = "Nina\nEvilLine"
    with pytest.raises(ValueError, match="quebra de linha"):
        render_env_local(data)


def test_render_env_local_escapes_or_rejects_newlines():
    """Test that env file values don't allow newline injection."""
    data = _sample_data()
    # Try to inject an extra env var via newline
    data.bot_name = "Nina\nEXTRA_VAR=malicious"
    with pytest.raises(ValueError, match="quebra de linha"):
        render_env_local(data)
