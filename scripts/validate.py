#!/usr/bin/env python3
"""Check that data/*.yaml follows the schema described in the README.

    python scripts/validate.py

Exit code 1 if anything is wrong (missing/duplicate ids, unknown university,
bad enum values, unsupported link schemes). Needs PyYAML.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset import load_courses, load_meta, load_universities  # noqa: E402

ACCESS = {"yes", "no", "conditional", None}
INTENSIVE = {"yes", "no", None}


def main() -> int:
    courses, unis, meta = load_courses(), load_universities(), load_meta()
    uni_ids = {u.get("id") for u in unis}
    errors: list[str] = []

    for u in unis:
        for key in ("id", "name", "short"):
            if not u.get(key):
                errors.append(f"universities.yaml: entry without {key!r}: {u}")

    seen: set[str] = set()
    for i, c in enumerate(courses):
        cid = c.get("id") or f"#{i}"
        where = c.get("_file", cid)
        if not c.get("id"):
            errors.append(f"{where}: missing id")
        elif c["id"] in seen:
            errors.append(f"{where}: duplicate id {cid}")
        seen.add(cid)
        if not (c.get("title") or "").strip():
            errors.append(f"{where}: empty title")
        if c.get("university_id") not in uni_ids:
            errors.append(f"{where}: unknown university_id {c.get('university_id')!r}")
        for key in ("online", "in_person"):
            if c.get(key) not in ACCESS:
                errors.append(f"{where}: {key}={c.get(key)!r} (use yes/no/conditional/null)")
        if c.get("intensive") not in INTENSIVE:
            errors.append(f"{where}: intensive={c.get('intensive')!r} (use yes/no/null)")
        if c.get("hours") is not None and not isinstance(c["hours"], (int, float)):
            errors.append(f"{where}: hours must be a number or null")
        for m in c.get("period_months", []):
            if not (isinstance(m, int) and 1 <= m <= 12):
                errors.append(f"{where}: bad month {m!r} in period_months (use 1-12)")
        for link in c.get("links", []):
            if not str(link.get("url", "")).lower().startswith(("http://", "https://", "mailto:")):
                errors.append(f"{where}: link with unsupported scheme {link.get('url')!r}")

    if not meta.get("site_title"):
        errors.append("meta.yaml: site_title is empty")

    print(f"{len(courses)} courses, {len(unis)} universities")
    for e in errors:
        print("  ERROR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
