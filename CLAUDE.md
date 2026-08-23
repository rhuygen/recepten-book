# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This repository is a recipe book. The recipes are written in Dutch. It
produces two outputs from the same Markdown source: a website, built with
MkDocs, and a PDF, built with Pandoc and Typst. Each recipe is one Markdown
file. Each Markdown file becomes one page on the website and one section in
the PDF.

## Commands

Set up a local environment (once):

```bash
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv/bin/python
brew install pandoc typst
```

Serve the website locally with live reload:

```bash
.venv/bin/mkdocs serve
```

Build the website into `site/`:

```bash
.venv/bin/mkdocs build --strict
```

Render the PDF straight from the recipe Markdown files, into `site/pdf/`,
so it is published together with the website:

```bash
python3 scripts/build_pdf.py src/recepten site/pdf/receptenboek.pdf
```

These two build steps are independent of each other and can run in any
order.

## Architecture

- `docs_dir` is set to `src`, not the MkDocs default `docs`. All source
  Markdown files live under `src/`.
- `src/index.md` is the home page of the website.
- `src/recepten/` holds one Markdown file per recipe, grouped into one
  subfolder per category (for example `Desserts`, `Soepen`). Add a new
  recipe by adding a new Markdown file to the right category folder. No
  other step is needed, for either the website or the PDF.
- `src/recepten/Images/` holds the recipe photos. Recipes reference them
  with a relative path, for example `../Images/erwtensoep.jpg`, always
  with plain Markdown image syntax (`![alt](path)`), never a raw HTML
  `<img>` tag. A raw `<img>` tag breaks on both outputs: MkDocs never
  rewrites the path inside it, so it resolves one directory too shallow
  under directory-style URLs, and Pandoc silently drops raw HTML `<img>`
  tags when writing Typst.
- A recipe's lead photo, when it wants a "beside the text" look instead of
  full-width, gets that from two independent places, since inline
  attribute syntax cannot be shared between them: MkDocs' attribute syntax
  (`{: width="30%" }`) and Pandoc's (`{width=30%}`) are mutually
  incompatible, so a single inline annotation cannot drive both outputs.
  - The website: `src/stylesheets/extra.css`, registered as `extra_css`
    in `mkdocs.yml`, floats a recipe's lead image automatically whenever
    the recipe's first paragraph is a single image. No per-recipe markup
    needed.
  - The PDF: Typst has no CSS-style float-with-text-reflow (see
    https://github.com/typst/typst/discussions/1069), so
    `scripts/build_pdf.py` instead places the image in a fixed two-column
    Typst grid next to one specific block, not flowing arbitrary content
    around it. It always pairs the image with the ingredients: it looks,
    after the image, for the first heading immediately followed by a
    list (whatever that section happens to be titled -- "Ingrediënten",
    "Benodigdheden", ...), and puts the image beside that heading and
    list. Everything between the image and that point (the title, any
    intro text) stays full-width, above it. A recipe with no such
    heading-and-list pair keeps its image full-width in the PDF.
- The `mkdocs-awesome-pages-plugin` builds the website's navigation menu
  from the folder structure. A new file under `src/recepten/` appears in
  the menu on the next build, in alphabetical order, with no edit to
  `mkdocs.yml`. The file `src/recepten/.pages` sets the display title of
  the section in the menu.
- `scripts/build_pdf.py` builds the PDF directly from `src/recepten/`,
  independently of the website build. It walks the category folders in the
  same alphabetical order the website's navigation menu uses, concatenates
  the recipe files with a Typst page break between each one, and pipes the
  result through `pandoc --pdf-engine=typst`.
- This project has already been through two other PDF pipelines, both
  built on top of the rendered website HTML, and both abandoned:
  - `mkdocs-with-pdf` (an MkDocs plugin, unmaintained since 2021): its
    custom HTML-merging logic silently dropped almost all recipe content.
  - `mkdocs-print-site-plugin` combined with a browser print engine
    (WeasyPrint, then headless Chromium through Playwright): this
    correctly assembled the content, but produced a poorly paginated PDF —
    blank pages after headings with little content beneath them, and
    figures split across a page boundary. Browser/CSS print engines do not
    give enough page-break and figure-placement control for book-quality
    output.

  Building directly from the Markdown source with Pandoc and Typst avoids
  both problems: Typst is a real typesetting engine, so it never splits a
  figure across pages and never leaves a page break somewhere content
  wasn't asked to break. Do not reintroduce an HTML-to-PDF step for this
  reason; if the PDF ever needs to change, change `scripts/build_pdf.py`
  or its Typst/Pandoc options instead.
- `.github/workflows/deploy.yml` builds the website and the PDF on every
  push to `main`, and publishes the `site/` folder (which now contains
  both) to the `gh-pages` branch with `peaceiris/actions-gh-pages`.
