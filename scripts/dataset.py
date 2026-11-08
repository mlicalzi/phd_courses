"""Load and export the course dataset (data/*.yaml). Needs PyYAML."""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

LIST_FIELDS = ("phd_programs", "emails", "period_months", "links")
TEXT_FIELDS = (
    "title", "referent_raw", "hours_raw", "period_raw", "intensive_raw",
    "in_person_raw", "online_raw", "program", "syllabus", "notes",
)

CSV_COLUMNS = [
    "id", "university", "phd_programs", "title", "referent", "emails",
    "hours", "hours_raw", "period", "period_months", "intensive", "intensive_raw",
    "open_in_person", "open_online", "program", "syllabus", "notes", "links",
]


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps `yes`, `no` and `2026-08-21` as plain text.

    Stock YAML 1.1 turns a bare `no` into False and a date into a date object, which
    would silently break the yes/no/conditional fields and `as_of`.
    """


_Loader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in resolvers
         if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def read_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=_Loader)
    return default if data is None else data


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def course_files() -> list[Path]:
    root = DATA / "courses"
    if not root.exists():
        return []
    return sorted(
        p for p in root.rglob("*")
        if p.suffix in (".yaml", ".yml") and not p.name.startswith(("_", "."))
    )


def load_courses() -> list[dict]:
    """One YAML file per course under data/courses/ (subfolders allowed).

    Files whose name starts with "_" are ignored (templates). `id` defaults to the file name; `university_id` defaults to the name of the
    subfolder, so data/courses/padova/foo.yaml needs neither.
    """
    root = DATA / "courses"
    courses = []
    for path in course_files():
        rec = read_yaml(path, {})
        if not isinstance(rec, dict):
            raise SystemExit(f"{path}: expected a mapping of fields")
        rec.setdefault("id", path.stem)
        if path.parent != root:
            rec.setdefault("university_id", path.parent.name)
        # a key left blank in YAML is None: turn it into an empty list / empty text
        for key in LIST_FIELDS:
            if rec.get(key) is None:
                rec[key] = []
        for key in TEXT_FIELDS:
            if rec.get(key) is None:
                rec[key] = ""
        rec["_file"] = str(path.relative_to(ROOT))
        courses.append(rec)
    return courses


def load_universities() -> list[dict]:
    return read_yaml(DATA / "universities.yaml", [])


def load_meta() -> dict:
    return read_yaml(DATA / "meta.yaml", {})


# -- tiny text helpers used by the site generator ---------------------------


def clean(text: str | None) -> str:
    """NBSP -> space, trim each line, collapse runs of blank lines."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("​", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def fold(text: str | None) -> str:
    """Lower-case and strip accents, for sorting and comparisons."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def academic_order(month: int) -> int:
    """Position of a month in the academic year (September = 0 ... August = 11)."""
    return (month - 9) % 12


def to_csv(courses: list[dict], universities: list[dict]) -> str:
    names = {u["id"]: u["name"] for u in universities}
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    for c in courses:
        w.writerow([
            c["id"],
            names.get(c["university_id"], c["university_id"]),
            " | ".join(c.get("phd_programs", [])),
            c["title"],
            c.get("referent_raw", ""),
            "; ".join(c.get("emails", [])),
            "" if c.get("hours") is None else c["hours"],
            c.get("hours_raw", ""),
            c.get("period_raw", ""),
            " ".join(str(m) for m in c.get("period_months", [])),
            c.get("intensive") or "",
            c.get("intensive_raw", ""),
            c.get("in_person") or "",
            c.get("online") or "",
            c.get("program", ""),
            c.get("syllabus", ""),
            c.get("notes", ""),
            " ".join(l["url"] for l in c.get("links", []) if not l["url"].startswith("mailto:")),
        ])
    return buf.getvalue()
