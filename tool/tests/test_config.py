from pathlib import Path

import pytest

from ste_lint.config import Config, ConfigError


def test_load_walks_up_and_parses(tmp_path: Path):
    (tmp_path / ".ste-lint.toml").write_text(
        'mode = "procedural"\ntechnical_nouns = ["flange/n"]\ndisable = ["8.1"]\n'
        '[severity_overrides]\n"1.1-unknown" = "info"\n[inputs.strings]\ninclude = ["src/**/*.json"]\n')
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    c = Config.load(sub)
    assert c.mode == "procedural" and c.technical_nouns == {"flange/n"} and c.disable == {"8.1"}
    assert c.severity_overrides == {"1.1-unknown": "info"} and c.string_include == ["src/**/*.json"]
    assert c.root == str(tmp_path)


def test_add_allow_roundtrip(tmp_path: Path):
    c = Config.load(tmp_path)
    c.root = str(tmp_path)
    c.add_allow("webhook/n", verb=False)
    c.add_allow("deploy/v", verb=True)
    c2 = Config.load(tmp_path)
    assert c2.technical_nouns == {"webhook/n"} and c2.technical_verbs == {"deploy/v"}


@pytest.mark.parametrize("toml, fragment", [
    ('mode = "Procedural"\n', "invalid mode 'Procedural'"),
    ('fail_on = "fatal"\n', "invalid fail_on 'fatal'"),
    ('[severity_overrides]\n"1.1" = "critical"\n', "invalid severity 'critical' for rule '1.1'"),
    ('mode = "procedural\n', "cannot parse"),
])
def test_load_rejects_invalid_values(tmp_path: Path, toml, fragment):
    (tmp_path / ".ste-lint.toml").write_text(toml)
    with pytest.raises(ConfigError) as exc:
        Config.load(tmp_path)
    assert fragment in str(exc.value) and ".ste-lint.toml" in str(exc.value)
    assert issubclass(ConfigError, ValueError)


def test_global_config_is_validated_too(tmp_path: Path, monkeypatch):
    g = tmp_path / "global.toml"
    g.write_text('mode = "nope"\n')
    monkeypatch.setattr("ste_lint.config.GLOBAL_FILE", g)
    with pytest.raises(ConfigError, match="global.toml"):
        Config.load(tmp_path)


def test_global_config_is_isolated_in_tests(tmp_path: Path):
    from ste_lint import config as cfg

    assert not cfg.GLOBAL_FILE.exists()
