"""Deriva um slug técnico seguro pra recursos AWS a partir do nome do bot."""

from __future__ import annotations

import re
import unicodedata

_MAX_SLUG_LEN = 20
_VALID_SLUG = re.compile(r"[a-z0-9](-?[a-z0-9])*")


def slugify(bot_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", bot_name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = re.sub(r"-+", "-", slug)
    slug = slug[:_MAX_SLUG_LEN].strip("-")
    return slug or "bot"


def is_valid_slug(slug: str) -> bool:
    return bool(_VALID_SLUG.fullmatch(slug)) and 1 <= len(slug) <= _MAX_SLUG_LEN
