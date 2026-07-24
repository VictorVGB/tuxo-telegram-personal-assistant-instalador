from tuxo.agent.system_prompt import build_system_prompt


def test_default_bot_name_is_tuxo():
    prompt = build_system_prompt("123", "America/Sao_Paulo")
    assert "Você é o **Tuxo**" in prompt


def test_custom_bot_name_is_used():
    prompt = build_system_prompt("123", "America/Sao_Paulo", bot_name="Nina")
    assert "Você é o **Nina**" in prompt
    assert "Tuxo" not in prompt
