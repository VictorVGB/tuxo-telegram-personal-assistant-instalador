from __future__ import annotations

import re


def md_to_html(text: str) -> str:
    """Converte Obsidian Markdown para HTML do Telegram."""
    protected: list[str] = []

    def protect(html: str) -> str:
        protected.append(html)
        return f"\x00P{len(protected) - 1}\x00"

    def protect_fenced(m: re.Match) -> str:  # type: ignore[type-arg]
        return protect(f"<pre>{_escape(m.group(1) or '')}</pre>")

    def protect_inline(m: re.Match) -> str:  # type: ignore[type-arg]
        return protect(f"<code>{_escape(m.group(1))}</code>")

    def protect_frontmatter(m: re.Match) -> str:  # type: ignore[type-arg]
        return protect(f"<pre>{_escape(m.group(1))}</pre>") + "\n"

    text = re.sub(r"```[^\n]*\n(.*?)```", protect_fenced, text, flags=re.DOTALL)
    text = re.sub(r"`([^`\n]+)`", protect_inline, text)
    text = re.sub(r"^---\n(.*?)\n---\n?", protect_frontmatter, text, count=1, flags=re.DOTALL)

    text = _escape(text)

    _callouts = {"tip": "💡", "warning": "⚠️", "todo": "☑️", "note": "📝"}

    def replace_callout(m: re.Match) -> str:  # type: ignore[type-arg]
        emoji = _callouts.get(m.group(1).lower(), "📌")
        rest = m.group(2).strip()
        return f"{emoji} {rest}" if rest else emoji

    text = re.sub(r"&gt; \[!(\w+)\](.*)", replace_callout, text)
    text = re.sub(r"^&gt; ?", "", text, flags=re.MULTILINE)

    text = re.sub(r"^#{1,6} (.+)$", lambda m: f"<b>{m.group(1)}</b>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    text = re.sub(
        r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
        lambda m: m.group(2) or m.group(1),
        text,
    )

    for i, block in enumerate(protected):
        text = text.replace(f"\x00P{i}\x00", block)

    return text


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
