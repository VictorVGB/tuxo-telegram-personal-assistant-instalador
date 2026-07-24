from instalador.steps.bot_identity import slugify, is_valid_slug


def test_slugify_simple_name():
    assert slugify("Nina") == "nina"


def test_slugify_removes_accents_and_symbols():
    assert slugify("São João!!") == "sao-joao"


def test_slugify_truncates_long_names():
    result = slugify("a" * 40)
    assert len(result) <= 20


def test_slugify_never_empty():
    assert slugify("!!!") == "bot"


def test_is_valid_slug_accepts_generated_slugs():
    assert is_valid_slug(slugify("Nina")) is True
    assert is_valid_slug(slugify("São João!!")) is True


def test_is_valid_slug_rejects_uppercase():
    assert is_valid_slug("Nina") is False


def test_is_valid_slug_rejects_empty():
    assert is_valid_slug("") is False
