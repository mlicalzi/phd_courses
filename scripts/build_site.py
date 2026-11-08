#!/usr/bin/env python3
"""Generate the static site (site/) from data/*.yaml.

    python scripts/build_site.py            # writes ./site
    python scripts/build_site.py --out dist

No third-party packages: HTML is produced with the standard library, and the
output uses only relative links, so it works from any GitHub Pages sub-path.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset import (  # noqa: E402
    ROOT, academic_order, clean, fold, load_courses, load_meta, load_universities,
    to_csv, write_json,
)

MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL = ["", "January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
ACADEMIC_MONTHS = sorted(range(1, 13), key=academic_order)  # Sep ... Aug

PLAIN_INTENSIVE = {"si", "yes", "intensivo", "no", "standard"}

esc = html.escape


# --------------------------------------------------------------------------
# small HTML helpers
# --------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s<>\"]+")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")


def linkify(text: str) -> str:
    """Escape ``text`` and turn bare URLs / e-mail addresses into links."""
    out = esc(text, quote=False)

    def url(m: re.Match) -> str:
        u = m.group(0)
        tail = ""
        while u and u[-1] in ".,;:)":
            tail = u[-1] + tail
            u = u[:-1]
        return f'<a href="{u}" rel="noopener noreferrer">{u}</a>{tail}'

    out = _URL_RE.sub(url, out)

    def mail(m: re.Match) -> str:
        # leave addresses already inside an href / link text alone
        start = m.start()
        before = out[max(0, start - 8):start]
        if before.endswith(("mailto:", "://")) or out[start - 1:start] in {"/", ">"}:
            return m.group(0)
        e = m.group(0).strip(".")
        return f'<a href="mailto:{e}">{e}</a>'

    parts = re.split(r"(<a .*?</a>)", out)
    parts = [p if p.startswith("<a ") else _EMAIL_RE.sub(mail, p) for p in parts]
    return "".join(parts)


def paragraphs(text: str) -> str:
    """Multi-line free text -> escaped, linkified HTML keeping line breaks."""
    text = clean(text)
    return f'<div class="prose">{linkify(text)}</div>' if text else ""


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


# --------------------------------------------------------------------------
# course entry
# --------------------------------------------------------------------------

ACCESS_LABEL = {"yes": "yes", "no": "no", "conditional": "on conditions", None: "not stated"}
ACCESS_MARK = {"yes": "✓", "no": "✗", "conditional": "~", None: "?"}


def access_pill(label: str, value: str | None) -> str:
    cls = value or "unknown"
    return (
        f'<span class="pill {cls}"><span aria-hidden="true">{ACCESS_MARK[value]}</span> '
        f'{label}<span class="sr-only">: {ACCESS_LABEL[value]}</span></span>'
    )


def fact(label: str, value_html: str) -> str:
    return f"<div><dt>{label}</dt><dd>{value_html}</dd></div>"


def render_course(c: dict) -> str:
    facts = []
    hours_raw = clean(c.get("hours_raw"))
    if c.get("hours") is not None:
        facts.append(fact("Hours", f'{c["hours"]:g}&nbsp;h'))
    elif hours_raw:
        facts.append(fact("Hours", esc(hours_raw)))

    period = clean(c.get("period_raw"))
    if period:
        shown = esc(period).replace("; ", ";<br>") if len(period) > 70 else esc(period)
        facts.append(fact("Period", shown))

    raw_int = clean(c.get("intensive_raw"))
    if raw_int:
        if fold(raw_int).strip(" .*") in PLAIN_INTENSIVE:
            label = {"yes": "Intensive", "no": "Not intensive"}.get(c.get("intensive"), esc(raw_int))
        else:
            label = esc(raw_int)
        facts.append(fact("Schedule", label))

    access = (
        access_pill("In person", c.get("in_person")) + " " + access_pill("Online", c.get("online"))
    )
    notes_cond = []
    if c.get("in_person") == "conditional":
        notes_cond.append(f'In person: {esc(clean(c["in_person_raw"]))}')
    if c.get("online") == "conditional":
        notes_cond.append(f'Online: {esc(clean(c["online_raw"]))}')
    if notes_cond:
        access += '<small class="cond">' + "<br>".join(notes_cond) + "</small>"
    facts.append(fact("Open to external students", access))

    referent = clean(c.get("referent_raw"))
    if referent:
        facts.append(fact("Contact", linkify(referent).replace("\n", "<br>")))

    programs = " · ".join(esc(p) for p in c.get("phd_programs", []))

    body = []
    if clean(c.get("program")):
        body.append(f"<h4>General programme</h4>{paragraphs(c['program'])}")
    if clean(c.get("syllabus")):
        body.append(f"<h4>Syllabus</h4>{paragraphs(c['syllabus'])}")
    detail = ""
    if body:
        detail = f'<details class="more"><summary>Programme and syllabus</summary>{"".join(body)}</details>'

    note = ""
    if clean(c.get("notes")):
        note = f'<p class="note"><strong>Note.</strong> {linkify(clean(c["notes"]))}</p>'

    months = " ".join(str(m) for m in c.get("period_months", []))
    return (
        f'<li class="course" id="{esc(c["id"])}" data-uni="{esc(c["university_id"])}" '
        f'data-online="{c.get("online") or ""}" data-inperson="{c.get("in_person") or ""}" '
        f'data-months="{months}">\n'
        f'  <h3><a class="permalink" href="#{esc(c["id"])}">{esc(c["title"])}</a></h3>\n'
        + (f'  <p class="programs">{programs}</p>\n' if programs else "")
        + f'  <dl class="facts">{"".join(facts)}</dl>\n'
        f"  {detail}\n  {note}\n</li>"
    )


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------


def site_nav(active: str, meta: dict) -> str:
    items = [("index.html", "Courses", "courses"), ("stats.html", "Statistics", "stats")]
    links = []
    for href, label, key in items:
        current = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{href}"{current}>{label}</a>')
    links.append('<a href="courses.csv">CSV</a>')
    links.append('<a href="courses.json">JSON</a>')
    if meta.get("repo_url"):
        links.append(f'<a href="{esc(meta["repo_url"])}">GitHub</a>')
    return "".join(links)


def footer(meta: dict) -> str:
    bits = []
    if meta.get("as_of"):
        bits.append(f'Information collected as of {esc(meta["as_of"])}.')
    if meta.get("working_group"):
        bits.append("Working group: " + esc(", ".join(meta["working_group"])) + ".")
    if meta.get("contact_email"):
        e = esc(meta["contact_email"])
        bits.append(f'Corrections and new courses: <a href="mailto:{e}">{e}</a>.')
    else:
        bits.append("Corrections and proposals for new courses go to any member of the working group.")
    bits.append(
        "Data are published as <a href=\"courses.csv\">CSV</a> and <a href=\"courses.json\">JSON</a>; "
        "text is reproduced as supplied by each university."
    )
    return "<p>" + " ".join(bits) + "</p>"


def render_index(courses, unis, meta) -> str:
    by_uni: dict[str, list[dict]] = {}
    for c in courses:
        by_uni.setdefault(c["university_id"], []).append(c)
    unis_sorted = sorted((u for u in unis if u["id"] in by_uni), key=lambda u: fold(u["short"]))

    ay =meta.get("academic_year", "").replace("-", "–")
    stats_line = " · ".join(
        x for x in [
            f"Academic year {esc(ay)}" if ay else "",
            f"collected {esc(meta['as_of'])}" if meta.get("as_of") else "",
            plural(len(courses), "course"),
            plural(len(unis_sorted), "university", "universities"),
        ] if x
    )

    en = meta.get("intro_en", [])
    intro_en = f"<p>{esc(en[0])}</p>" if en else ""
    if len(en) > 1:
        intro_en += (
            '<details class="about"><summary>About this inventory</summary>'
            + "".join(f"<p>{esc(p)}</p>" for p in en[1:])
            + "</details>"
        )
    intro_it = "".join(f"<p>{esc(p)}</p>" for p in meta.get("intro_it", []))

    uni_options = "".join(
        f'<option value="{esc(u["id"])}">{esc(u["short"])} ({len(by_uni[u["id"]])})</option>' for u in unis_sorted
    )
    month_options = "".join(f'<option value="{m}">{MONTH_FULL[m]}</option>' for m in ACADEMIC_MONTHS)

    nav = "".join(
        f'<a href="#u-{esc(u["id"])}" data-uni="{esc(u["id"])}">{esc(u["short"])}'
        f'<span class="n">{len(by_uni[u["id"]])}</span></a>'
        for u in unis_sorted
    )

    sections = []
    for u in unis_sorted:
        items = "\n".join(render_course(c) for c in by_uni[u["id"]])
        sections.append(
            f'<section class="uni" id="u-{esc(u["id"])}" data-uni="{esc(u["id"])}">\n'
            f'<h2>{esc(u["name"])} <span class="count">{len(by_uni[u["id"]])}</span></h2>\n'
            f'<ul class="courses">\n{items}\n</ul>\n</section>'
        )

    content = f"""
<h1>{esc(meta.get("site_title", "PhD courses"))}</h1>
<p class="subtitle">{esc(meta.get("subtitle", ""))}</p>
<div class="intro">{intro_en}</div>
<p class="stats-line">{stats_line}</p>
<details class="it"><summary>Testo originale in italiano</summary>{intro_it}</details>

<form class="filters" role="search" aria-label="Filter courses" onsubmit="return false">
  <label class="f-q"><span>Search</span>
    <input type="search" id="q" placeholder="title, topic, syllabus, contact…" autocomplete="off"></label>
  <label><span>University</span>
    <select id="f-uni"><option value="">All universities</option>{uni_options}</select></label>
  <label><span>Month</span>
    <select id="f-month"><option value="">Any month</option>{month_options}</select></label>
  <fieldset class="f-checks"><legend>Open to external students</legend>
    <label class="chk"><input type="checkbox" id="f-inperson"> in person</label>
    <label class="chk"><input type="checkbox" id="f-online"> online</label>
  </fieldset>
  <button type="reset" id="f-reset" class="ghost">Reset</button>
</form>

<nav class="uni-nav" aria-label="Universities">{nav}<a class="top" href="#main">↑ top</a></nav>
<p id="result-count" class="result-count" aria-live="polite"></p>
<p id="no-results" class="no-results" hidden>No course matches these filters.</p>

{"".join(sections)}
"""
    return content


def bar_rows(rows: list[tuple[str, int]]) -> str:
    top = max((n for _, n in rows), default=0) or 1
    out = []
    for label, n in rows:
        w = round(100 * n / top, 1)
        out.append(
            f'<li><span class="lbl">{label}</span>'
            f'<span class="track"><span class="fill" style="width:{w}%"></span></span>'
            f'<span class="num">{n}</span></li>'
        )
    return f'<ul class="bars">{"".join(out)}</ul>'


def render_stats(courses, unis, meta) -> str:
    names = {u["id"]: u["short"] for u in unis}
    n = len(courses)

    by_uni = Counter(c["university_id"] for c in courses)
    uni_rows = [(esc(names.get(k, k)), v) for k, v in sorted(by_uni.items(), key=lambda kv: (-kv[1], fold(names.get(kv[0], kv[0]))))]

    month_counts = Counter(m for c in courses for m in c.get("period_months", []))
    month_rows = [(MONTH_FULL[m], month_counts.get(m, 0)) for m in ACADEMIC_MONTHS]
    no_month = sum(1 for c in courses if not c.get("period_months"))

    buckets = [("up to 10 h", -1, 10), ("more than 10 and up to 15 h", 10, 15),
               ("more than 15 and up to 20 h", 15, 20), ("more than 20 and up to 30 h", 20, 30),
               ("more than 30 h", 30, float("inf"))]
    hours = [c["hours"] for c in courses if c.get("hours") is not None]
    hour_rows = [(label, sum(1 for h in hours if lo < h <= hi)) for label, lo, hi in buckets]
    hour_rows.append(("not a single number", len(courses) - len(hours)))

    def access_rows(key):
        cnt = Counter(c.get(key) for c in courses)
        return [("yes", cnt["yes"]), ("no", cnt["no"]), ("on conditions", cnt["conditional"]), ("not stated", cnt[None])]

    int_cnt = Counter(c.get("intensive") for c in courses)
    fmt_rows = [("intensive", int_cnt["yes"]), ("not intensive", int_cnt["no"]),
                ("described in free text / blank", int_cnt[None])]

    mailto_n = sum(1 for c in courses if c.get("emails"))

    return f"""
<h1>Statistics</h1>
<p class="subtitle">Counts computed from the {n} courses currently in the archive.</p>

<div class="stat-grid">
  <div class="tile"><b>{n}</b><span>courses</span></div>
  <div class="tile"><b>{len(by_uni)}</b><span>universities</span></div>
  <div class="tile"><b>{sum(1 for c in courses if c.get("in_person") == "yes")}</b><span>open to external students in person</span></div>
  <div class="tile"><b>{sum(1 for c in courses if c.get("online") == "yes")}</b><span>open to external students online</span></div>
</div>

<section class="stat"><h2>Courses by university</h2>{bar_rows(uni_rows)}</section>

<section class="stat"><h2>Courses by month</h2>
<p class="hint">A course counts in every month it runs, September to August. {no_month} courses give a period that
cannot be read as months (for example “I semestre” or “Spring semester”) and are not counted here.</p>
{bar_rows(month_rows)}</section>

<section class="stat"><h2>Hours</h2>
<p class="hint">Only entries that are a single number are bucketed (“30 ore accademiche” counts as 30).</p>
{bar_rows(hour_rows)}</section>

<section class="stat two"><div><h2>Open to external students: in person</h2>{bar_rows(access_rows("in_person"))}</div>
<div><h2>Open to external students: online</h2>{bar_rows(access_rows("online"))}</div></section>

<section class="stat"><h2>Schedule</h2>{bar_rows(fmt_rows)}</section>

<p class="hint">{mailto_n} of {n} courses list a contact e-mail address.</p>
"""


# --------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the static site")
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    args = ap.parse_args(argv)
    out: Path = args.out

    courses = load_courses()
    unis = load_universities()
    meta = load_meta()
    if not courses:
        sys.exit("no courses found - add YAML files under data/courses/ (see README)")

    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    for asset in (ROOT / "assets").iterdir():
        shutil.copy2(asset, out / "assets" / asset.name)

    template = Template((ROOT / "templates" / "page.html").read_text(encoding="utf-8"))
    site_title = meta.get("site_title", "PhD courses")

    def page(filename: str, title: str, content: str, active: str, scripts: str = "", body_class: str = "") -> None:
        text = template.substitute(
            title=esc(title),
            description=esc(meta.get("subtitle", "")),
            site_title=esc(site_title),
            site_nav=site_nav(active, meta),
            content=content,
            footer=footer(meta),
            scripts=scripts,
            body_class=body_class,
        )
        (out / filename).write_text(text, encoding="utf-8")

    page("index.html", site_title, render_index(courses, unis, meta), "courses",
         scripts='<script src="assets/filter.js" defer></script>', body_class="p-index")
    page("stats.html", f"Statistics – {site_title}", render_stats(courses, unis, meta), "stats", body_class="p-stats")

    public = [{k: v for k, v in c.items() if not k.startswith("_")} for c in courses]
    write_json(out / "courses.json", public)
    (out / "courses.csv").write_text(to_csv(courses, unis), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"built {len(courses)} courses -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
