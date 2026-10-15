import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REAL_PDF = Path.home() / "Downloads" / "asd-ste100-issue-9.pdf"


@pytest.fixture(autouse=True)
def isolate_global_config(monkeypatch, tmp_path):
    """Never let the developer's real ~/.config/ste-lint/config.toml leak into tests."""
    monkeypatch.setattr("ste_lint.config.GLOBAL_FILE", tmp_path / "no-such-global-config.toml")


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def lexicon():
    """A Lexicon built from the committed mini dictionary fixture."""
    from ste_lint.engine.lexicon import Lexicon

    return Lexicon.from_dict(json.loads((FIXTURES / "mini_dictionary.json").read_text()))


@pytest.fixture(scope="session")
def mini_lexicon():
    from ste_lint.engine.lexicon import Lexicon

    return Lexicon.from_dict(json.loads((FIXTURES / "mini_dictionary.json").read_text()))


@pytest.fixture(scope="session")
def nlp():
    from ste_lint.engine.pipeline import load_nlp

    return load_nlp()


@pytest.fixture
def lint(mini_lexicon, nlp):
    from ste_lint.config import Config
    from ste_lint.engine.pipeline import lint_text

    def _lint(text, mode="descriptive", kind="paragraph", **cfg):
        config = Config.default()
        config.mode = mode
        for k, v in cfg.items():
            setattr(config, k, v)
        return lint_text(text, mini_lexicon, config, kind=kind)

    return _lint


def pytest_collection_modifyitems(config, items):
    from ste_lint import DICTIONARY_PATH

    for item in items:
        if "corpus" in item.keywords and not (REAL_PDF.exists() and DICTIONARY_PATH.exists()):
            item.add_marker(pytest.mark.skip(reason="real PDF/dictionary not present"))
