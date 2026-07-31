"""i18n loader tests — macrons-on-te-reo protection."""

import json
from pathlib import Path
from typing import Any

from kaitiaki_carbon.i18n import t


class TestResolveKnownKey:
    def test_resolves_estimate_running_english(self) -> None:
        s = t("cli.estimate.running", "en")
        assert "biomass" in s

    def test_resolves_estimate_running_maori(self) -> None:
        s = t("cli.estimate.running", "mi")
        # The te reo string should be present (whatever it says)
        assert isinstance(s, str) and len(s) > 0

    def test_unknown_locale_falls_back_to_english(self) -> None:
        s = t("cli.estimate.running", "fr")  # type: ignore[arg-type]
        assert "biomass" in s


class TestMacronProtection:
    def test_known_macron_keys_resolve(self) -> None:
        # i18n strings should have macrons. The running key has "warо" not "waro".
        s = t("cli.estimate.running", "mi")
        assert any(ch in "āēīōū" for ch in s)

    def test_missing_key_falls_back_to_english(self) -> None:
        s = t("cli.nonexistent.fake.key", "mi")
        # Falls back to the English catalogue, which falls back to the key
        # itself since both catalogues lack this key. We expect: "cli.nonexistent.fake.key"
        assert s == "cli.nonexistent.fake.key"


class TestFormatting:
    def test_named_args_substituted(self) -> None:
        s = t(
            "cli.estimate.result_headline",
            "en",
            estimate_tCO2e=1200.5,
            ci_low=1100.0,
            ci_high=1300.0,
        )
        assert "1200.5" in s
        assert "1100.0" in s
        assert "1300.0" in s

    def test_te_reo_named_args_substituted(self) -> None:
        s = t(
            "cli.estimate.result_headline",
            "mi",
            estimate_tCO2e=1200.5,
            ci_low=1100.0,
            ci_high=1300.0,
        )
        assert "1200.5" in s
        assert "1100.0" in s
        assert "1300.0" in s


class TestCatalogueCompleteness:
    def test_every_english_key_has_a_te_reo_translation(self) -> None:
        """Brute-force parity: every key path in en.json must exist in mi.json.

        If this test fails, an English-only string was added. Run:
          python -c "from kaitiaki_carbon.i18n import t; print(t('cli.the.new.key', 'mi'))"
        to see what was missed.
        """
        here = Path(__file__).resolve().parent.parent / "src" / "kaitiaki_carbon" / "i18n"

        def walk(d: dict[str, Any], path: str = "") -> list[str]:
            out: list[str] = []
            for k, v in d.items():
                new_path = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    out.extend(walk(v, new_path))
                else:
                    out.append(new_path)
            return out

        en_keys = set(walk(json.loads((here / "en.json").read_text(encoding="utf-8"))))
        mi_keys = set(walk(json.loads((here / "mi.json").read_text(encoding="utf-8"))))

        missing_in_mi = en_keys - mi_keys
        assert not missing_in_mi, (
            f"English-only keys (need mi translations): {sorted(missing_in_mi)}"
        )

    def test_every_te_reo_key_has_an_english_translation(self) -> None:
        here = Path(__file__).resolve().parent.parent / "src" / "kaitiaki_carbon" / "i18n"

        def walk(d: dict[str, Any], path: str = "") -> list[str]:
            out: list[str] = []
            for k, v in d.items():
                new_path = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    out.extend(walk(v, new_path))
                else:
                    out.append(new_path)
            return out

        en_keys = set(walk(json.loads((here / "en.json").read_text(encoding="utf-8"))))
        mi_keys = set(walk(json.loads((here / "mi.json").read_text(encoding="utf-8"))))

        missing_in_en = mi_keys - en_keys
        assert not missing_in_en, (
            f"Te reo-only keys (need English translations): {sorted(missing_in_en)}"
        )
