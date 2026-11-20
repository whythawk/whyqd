# SPDX-License-Identifier: BSD-3-Clause
"""Write the month, weekday, and day-period names whyqd reads, per language, from Unicode's CLDR through Babel.

    python tests/data/builders/names.py [target]

Target defaults to whyqd/config/names.json and is never overwritten. Whyqd reads only the file, so a date never depends
on a library's version or a machine's locale, and changing it is a change to how a cell reads. Every region's spellings
of a language are kept, in each script Babel treats as that language's default, so English holds both `Sep` and `Sept`.
A spelling two months share is left out, since it could not say which it meant.
"""

import json
import sys
from pathlib import Path

import babel
from babel import Locale
from babel.localedata import locale_identifiers

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "whyqd" / "config" / "names.json"
FORMS = ("wide", "abbreviated")
CONTEXTS = ("format", "stand-alone")


def spellings(names, *keys) -> set[str]:
    found = set()
    for context in CONTEXTS:
        for form in FORMS:
            table = names.get(context, {}).get(form, {})
            found |= {table[key] for key in keys if key in table}
    return found


def key(name: str) -> str:
    return name.lower().rstrip(".")


def main() -> None:
    assert not TARGET.exists(), f"{TARGET} exists; fixtures are never overwritten"
    languages = {}
    for identifier in locale_identifiers():
        locale = Locale.parse(identifier)
        if locale.script:
            continue
        held = languages.setdefault(
            locale.language,
            {"months": [set() for _ in range(12)], "weekdays": set(), "morning": set(), "afternoon": set()},
        )
        for month in range(1, 13):
            held["months"][month - 1] |= spellings(locale.months, month)
        held["weekdays"] |= spellings(locale.days, *range(7))
        held["morning"] |= spellings(locale.day_periods, "am")
        held["afternoon"] |= spellings(locale.day_periods, "pm")
    written = {}
    for language, held in languages.items():
        seen = {}
        for month, names in enumerate(held["months"]):
            for name in names:
                seen.setdefault(key(name), set()).add(month)
        months = [sorted(n for n in names if len(seen[key(n)]) == 1) for names in held["months"]]
        if all(months):
            written[language] = {
                "months": months,
                "weekdays": sorted(held["weekdays"]),
                "morning": sorted(held["morning"] - held["afternoon"]),
                "afternoon": sorted(held["afternoon"] - held["morning"]),
            }
    document = {"source": "Unicode CLDR", "babel": babel.__version__, "languages": written}
    TARGET.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(len(written), "languages,", TARGET.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
