from tuxo.telegram.md_to_html import md_to_html


def test_plain_text():
    assert md_to_html("Olá mundo") == "Olá mundo"


def test_html_escape():
    assert md_to_html("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_bold():
    assert md_to_html("texto **negrito** aqui") == "texto <b>negrito</b> aqui"


def test_italic_asterisk():
    assert md_to_html("texto *italico* aqui") == "texto <i>italico</i> aqui"


def test_italic_underscore():
    assert md_to_html("texto _italico_ aqui") == "texto <i>italico</i> aqui"


def test_heading_h1():
    assert md_to_html("# Título") == "<b>Título</b>"


def test_heading_h2():
    assert md_to_html("## Título") == "<b>Título</b>"


def test_heading_h3():
    assert md_to_html("### Título") == "<b>Título</b>"


def test_wikilink():
    assert md_to_html("ver [[Nome da Nota]] aqui") == "ver Nome da Nota aqui"


def test_wikilink_with_spaces():
    assert md_to_html("[[Cidade São Paulo]]") == "Cidade São Paulo"


def test_inline_code():
    assert md_to_html("`code`") == "<code>code</code>"


def test_inline_code_not_processed():
    assert md_to_html("`**not bold**`") == "<code>**not bold**</code>"


def test_code_block():
    assert md_to_html("```\nprint('hello')\n```") == "<pre>print('hello')\n</pre>"


def test_code_block_with_lang():
    assert md_to_html("```python\nprint('hello')\n```") == "<pre>print('hello')\n</pre>"


def test_code_block_html_escaped():
    assert md_to_html("```\na < b\n```") == "<pre>a &lt; b\n</pre>"


def test_callout_tip():
    assert md_to_html("> [!tip] Use isso") == "💡 Use isso"


def test_callout_warning():
    assert md_to_html("> [!warning] Cuidado") == "⚠️ Cuidado"


def test_callout_todo():
    assert md_to_html("> [!todo] Fazer isso") == "☑️ Fazer isso"


def test_callout_note():
    assert md_to_html("> [!note] Observação") == "📝 Observação"


def test_callout_continuation():
    text = "> [!tip] Título\n> continuação"
    assert md_to_html(text) == "💡 Título\ncontinuação"


def test_frontmatter():
    text = "---\ntitle: Nota\ndate: 2026-07-01\n---\nConteúdo"
    result = md_to_html(text)
    assert result.startswith("<pre>")
    assert "title: Nota" in result
    assert "date: 2026-07-01" in result
    assert "Conteúdo" in result


def test_frontmatter_not_processed_for_bold():
    text = "---\ntitle: **Não Bold**\n---\nTexto"
    result = md_to_html(text)
    assert "<b>Não Bold</b>" not in result
    assert "**Não Bold**" in result


def test_combined():
    text = "## Título\n\nTexto com **negrito** e [[Wikilink]]."
    result = md_to_html(text)
    assert result == "<b>Título</b>\n\nTexto com <b>negrito</b> e Wikilink."


def test_wikilink_with_alias():
    assert md_to_html("ver [[Nota|Texto Display]] aqui") == "ver Texto Display aqui"


def test_wikilink_no_alias_unchanged():
    assert md_to_html("[[Nota Simples]]") == "Nota Simples"
