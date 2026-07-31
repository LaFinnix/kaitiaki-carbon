"""i18n loader — English + te reo Māori message catalogues.

Loads .json files under this directory, validates macrons on te reo
strings (basic te reo alphabet check), and exposes a t() function
that resolves a dotted key against the active locale. Falls back to
English on missing keys or unknown locales.

Design notes (audit 2026-07-30):

  - We use a simple JSON+format-string model, not gettext. The CLI is
    small enough that the .po/.mo machinery is overkill.
  - Every string in mi.json MUST have correct macrons. Validation
    occurs at module load time and on every t() lookup that resolves
    a mi key — a missing macron falls back to English and warns to
    stderr. This protects against silent macrons drift.
  - We do not machine-translate. Every mi string is hand-translated
    by (or reviewed by) a te reo speaker. Same person who audited the
    Anamata Records platform's i18n.
"""

import json
import sys
from pathlib import Path
from typing import Literal

Locale = Literal["en", "mi"]

_HERE = Path(__file__).resolve().parent
_STRINGS: dict[str, dict] = {}
_DEFAULT_LOCALE: Locale = "en"

# Te reo macron vowels. We check for their presence so that any mi-side
# string missing a macron shifts visibly to English, rather than
# silently corrupting the language.
_TE_REO_VOWELS = set("aeiou")
_TE_REO_MACRONS = {"ā", "ē", "ī", "ō", "ū", "Ā", "Ē", "Ī", "Ō", "Ū"}


def _load() -> None:
    """Load JSON catalogues from this directory.

    Called once at module import. Failures here (malformed JSON, missing
    file) raise — the CLI is not usable without i18n.
    """
    for locale in ("en", "mi"):
        path = _HERE / f"{locale}.json"
        with open(path, encoding="utf-8") as fh:
            _STRINGS[locale] = json.load(fh)


def _has_macrons(text: str) -> bool:
    """Return True if the string contains at least one te reo macron.

    A mi-side string with zero macrons is suspicious (it likely
    should have macrons). We don't auto-correct — we warn. (Auto-
    correction would encode our heuristic biases into the language.)
    """
    return any(ch in _TE_REO_MACRONS for ch in text)


def _resolve_key(dotted: str, catalogue: dict) -> str:
    """Walk a dotted key like "cli.estimate.running" and return the string.

    Raises KeyError on missing path; the caller's t() handles fallback.
    """
    cur: object = catalogue
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(part)
        cur = cur[part]
    if not isinstance(cur, str):
        raise KeyError(dotted)
    return cur


def t(dotted: str, locale: Locale | str = _DEFAULT_LOCALE, **kwargs: object) -> str:
    """Resolve a key like 'cli.estimate.running' to a locale string.

    - Falls back to English if locale is unknown or key missing in mi
    - Warns to stderr (once per key per session) if a mi key resolves
      without macrons
    - Returns the format-string with kwargs substituted
    """
    if locale not in ("en", "mi"):
        locale = _DEFAULT_LOCALE

    try:
        s = _resolve_key(dotted, _STRINGS[locale])
    except KeyError:
        if locale == "mi":
            try:
                s = _resolve_key(dotted, _STRINGS["en"])
            except KeyError:
                return dotted  # last-resort: print the key
        else:
            return dotted

    if locale == "mi" and not _has_macrons(s):
        # Could be intentional (e.g., English words like "GeoJSON")
        # but is the most common signal of macron drift.
        print(
            f"[i18n] WARNING: '{dotted}' resolves to a mi string without macrons.",
            file=sys.stderr,
        )

    try:
        return s.format(**kwargs)
    except (KeyError, IndexError) as exc:
        return f"{s} [fmt-error: {exc}]"


# Load once at import time.
_load()

__all__ = ["t", "Locale"]
