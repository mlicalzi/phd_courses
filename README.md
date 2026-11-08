# PhD Courses | SECS-S06

A list of doctoral courses in the SECS-S06 area. KISS applies.

This repository is a **scaffold**: the real entries still have to be added to `_data/courses.yml`.

## Layout

```
_config.yml              site title and description
_data/courses.yml        one entry per course  <- the file you edit
_data/meta.yml           intro texts (English draft + original Italian), as-of date, working group
_layouts/default.html    page shell
_includes/yn.html        prints Yes/No answers safely (see "YAML pitfall")
index.html               the page: groups courses by university
courses.json             the same data, for reuse (generated from _data/courses.yml)
assets/css/style.css     styles (the AMASES look, plus course entries)
assets/js/filter.js      free-text search (optional: the page works without JavaScript)
.github/workflows/pages.yml   builds with Jekyll and deploys to GitHub Pages
Gemfile                  optional, only for previewing on your own computer
```

## Adding a course

Append an entry to `_data/courses.yml`. The page groups entries by `university`, so spell the
university identically in every entry. The fields follow the SECS-S06 inventory:

```yaml
- university: Roma 1
  phd_program: "Denominazione dottorato"
  title: "Denominazione corso"
  url:                       # optional link for the title
  referent: "Name Surname (name.surname@uni.it)"
  hours: "30 ore accademiche"
  period: "Novembre - Dicembre"
  intensive: "No"
  in_person: "Sì"
  online: "No"
  programme: |
    General programme ("Programma di massima").
    Line breaks are kept.
  syllabus: |
    Syllabus.
  notes:
```

Only `university` and `title` are needed; empty fields are simply not shown. Text is displayed
exactly as written, so there is nothing to normalise.

**YAML pitfall.** Jekyll reads a bare `No`, `Yes`, `On` or `Off` as a boolean. Put short answers
in quotes (`online: "No"`). If you forget, the page still prints No/Yes thanks to
`_includes/yn.html`, but quoting keeps whatever the university wrote ("SI, obbligatoria").
A syntax error in the YAML makes the GitHub build fail, and the log shows the line.

## Publishing

1. Push to a GitHub repository (default branch `main`).
2. Settings, Pages, Source: **GitHub Actions**.
3. Every push to `main` rebuilds and deploys the site (workflow copied from AMASES_theses).

Links are built with Jekyll's `relative_url`, so the site works under
`https://<user>.github.io/<repo>/`.

## Previewing locally (optional)

You can skip this and just push. To preview you need Ruby:

```
bundle install
bundle exec jekyll serve
```

then open http://localhost:4000. On macOS the system Ruby is too old; install a recent one
(for example `brew install ruby`) first.

## To do before publishing

- Replace the two placeholder courses in `_data/courses.yml`.
- `intro_en` in `_data/meta.yml` is a draft translation of the Italian introduction; review it.
- The inventory lists contact persons with e-mail addresses. Check you are happy for them to
  be public.
- Add a `LICENSE` file once you have decided how the data may be reused.
