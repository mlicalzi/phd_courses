# PhD Courses in SECS-S06

A static, filterable archive of doctoral courses, modelled on
[stat04a.github.io/phd_theses](https://stat04a.github.io/phd_theses/) but shaped around the
fields of the *Corsi di dottorato – Area SECS-S06* inventory.

This repository is a **scaffold**: site generator, data schema, CI and two placeholder
entries. It contains no importer for the Word file; you fill `data/` yourself (or with any
tool you like) and the site builds from it. Data are plain YAML, one file per course.

## Layout

```
data/
  meta.yaml            site title, intro texts (EN + original IT), as-of date, working group
  universities.yaml    one entry per university (id, name, short name)
  courses/
    _template.yaml     fully commented template (ignored by the build)
    <university-id>/   one YAML file per course
      some-course.yaml
scripts/
  build_site.py        data/*.yaml -> site/
  validate.py          schema check, also run in CI
  dataset.py           YAML loading + CSV export
templates/page.html    page shell
assets/                style.css, filter.js (vanilla JS, no dependencies)
requirements.txt       PyYAML (the only dependency)
.github/workflows/pages.yml   validate, build, deploy to GitHub Pages
```

## Pages produced

- `index.html`: courses grouped by university, with a university bar (like the year bar of
  the theses site), free-text search, and filters for university, month and
  "open to external students" (in person / online). Filter state is kept in the URL.
- `stats.html`: courses by university and by month, hours, access to external students.
- `courses.json`, `courses.csv`: the same data for reuse.

## Data schema

`data/universities.yaml`: list of `{id, name, short, groups}`.

`data/courses/**/*.yaml`: one mapping per file. Required: `title`. `id` defaults to the file
name and `university_id` to the name of the folder the file sits in, so
`data/courses/padova/volterra-equations.yaml` needs neither (put them in the file to override).
Files whose name starts with `_` are ignored. `data/courses/_template.yaml` documents every
field with comments:

| field | type | meaning |
|---|---|---|
| `phd_programs` | list of text | PhD programme(s) the course belongs to |
| `referent_raw` | text | contact person, as shown |
| `emails` | list of text | contact e-mail addresses (used in the CSV) |
| `hours_raw` / `hours` | text / number | hours as written / a single number used in statistics |
| `period_raw` / `period_months` | text / list of 1-12 | period as written / calendar months it runs, used by the month filter and statistics |
| `intensive_raw` / `intensive` | text / `yes`, `no` | "Intensivo o meno" as written / classification |
| `in_person_raw` / `in_person` | text / `yes`, `no`, `conditional` | can external students attend in person |
| `online_raw` / `online` | text / `yes`, `no`, `conditional` | can external students attend online |
| `program` | text | "Programma di massima" |
| `syllabus` | text | syllabus; may be long (use a `|` block) |
| `notes` | text | notes |
| `links` | list of `{text, url}` | extra links (`http`, `https` or `mailto`) |

The `*_raw` text is what the page displays; the normalised twin only drives filters,
statistics and the CSV. Leave the twin out when the raw text cannot be reduced to a value.

**YAML pitfalls, handled here.** Standard YAML reads a bare `no` as the boolean false and
`2026-08-21` as a date. This project's loader switches both conversions off, so `no`, `yes` and
dates stay plain text and you can write them without quotes. Other tools reading these files
(for example a stock `yaml.safe_load`) will not do that.

## Local use

```
pip install -r requirements.txt
python scripts/validate.py
python scripts/build_site.py      # writes ./site
python -m http.server 8000 --directory site
```

or `make serve`. Python 3.10+.

## Publish on GitHub Pages

1. Push to a GitHub repository (default branch `main`).
2. Settings, Pages, Source: **GitHub Actions**.
3. Every push to `main` validates the data, builds the site and deploys it. Pull requests
   run the validation and build without deploying.

Links in the generated site are relative, so it works under `https://<user>.github.io/<repo>/`.

## To do before publishing

- Replace the placeholder university (`data/universities.yaml`) and the example courses
  (`data/courses/example-university/`).
- Set `contact_email` and `repo_url` in `data/meta.yaml` (both are empty, and the site
  simply omits them).
- `intro_en` is a draft translation of the Italian introduction; review it.
- The inventory lists contact persons with e-mail addresses. Check you are happy for them
  to be public before publishing.
- Add a licence file once you have decided how the data may be reused.
