"""Render all recipes straight from the Markdown source into one PDF.

This bypasses the MkDocs website build entirely and calls Pandoc, with
Typst as the PDF engine, directly on the recipe files under
docs/recepten/. Typst gives proper page-break and figure control, which a
browser-based, CSS-driven PDF pipeline could not (see CLAUDE.md).

For a recipe whose first block is a standalone image, the PDF places
that image beside the ingredients instead of full-width, mirroring the
"float right" look of the website (see docs/stylesheets/extra.css). Typst
has no CSS-style text reflow around a floating image, so this is a fixed
two-column layout instead: everything between the image and the first
heading-and-list pair (the title, and any intro text) stays full-width,
and the image is placed beside that heading-and-list pair itself.

A recipe may start with a small `main_ingredients` front matter block,
for example:

    ---
    main_ingredients: aardbeien, mascarpone
    ---

Every ingredient listed there is added to an ingredient index at the end
of the PDF, alongside the recipe's page number. The page numbers are
resolved by Typst itself at compile time (via a label on each recipe's
title and `query()`/`location()`), so they stay correct as recipes are
added, removed, or reordered -- nothing here hardcodes a page number.

Usage: python3 scripts/build_pdf.py <recipes_dir> <output_pdf_path>
"""

import glob
import os
import re
import subprocess
import sys
import tempfile

IMAGE_RE = re.compile(r"^!\[[^\]]*\]\(([^)]*)\)$")
H1_RE = re.compile(r"^#(?!#)\s+(.*)$")
LIST_ITEM_RE = re.compile(r"^(-|\*|\+|\d+\.)\s")
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?\n)---\n?", re.DOTALL)


def collect_recipes(recipes_dir: str) -> list[str]:
    categories = sorted(
        d for d in os.listdir(recipes_dir) if os.path.isdir(os.path.join(recipes_dir, d)) and d != "Images"
    )
    files = []
    for category in categories:
        files.extend(sorted(glob.glob(os.path.join(recipes_dir, category, "*.md"))))
    return files


def slugify(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return "recipe-" + re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()


def extract_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


def split_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n+", text.strip()) if b.strip()]


def is_heading(block: str) -> bool:
    return block.startswith("#")


def is_list(block: str) -> bool:
    return bool(LIST_ITEM_RE.match(block.splitlines()[0].strip()))


def markdown_to_typst(markdown: str) -> str:
    result = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "typst"],
        input=markdown,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def lead_image_grid(image_path: str, pair_markdown: str) -> str:
    pair_typst = markdown_to_typst(pair_markdown)
    image_literal = image_path.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "```{=typst}\n"
        "#grid(columns: (1fr, 30%), gutter: 1.5em, align: top,\n"
        "  [\n"
        f"{pair_typst}\n"
        "  ],\n"
        f'  image("{image_literal}", width: 100%),\n'
        ")\n"
        "```"
    )


def tag_title(blocks: list[str], slug: str) -> tuple[list[str], str]:
    """Add a Typst label to the recipe's title heading; return its plain text."""
    for i, block in enumerate(blocks):
        match = H1_RE.match(block)
        if match:
            blocks[i] = f"{block} {{#{slug}}}"
            return blocks, match.group(1).strip()
    return blocks, ""


def apply_lead_image_layout(path: str, blocks: list[str]) -> list[str]:
    if not blocks:
        return blocks

    match = IMAGE_RE.match(blocks[0])
    if not match:
        return blocks

    image_ref = match.group(1).replace("%20", " ")
    image_path = os.path.normpath(os.path.join(os.path.dirname(path), image_ref))
    rest = blocks[1:]

    # Find the first heading immediately followed by a list (the
    # ingredients, whatever that section happens to be titled) and pair
    # the image with that. Everything before it -- title, intro text --
    # stays full-width.
    pair_index = next(
        (i for i in range(len(rest) - 1) if is_heading(rest[i]) and is_list(rest[i + 1])),
        None,
    )
    if pair_index is None:
        return blocks

    before = rest[:pair_index]
    pair_blocks = rest[pair_index : pair_index + 2]
    after = rest[pair_index + 2 :]

    grid = lead_image_grid(image_path, "\n\n".join(pair_blocks))
    return before + [grid] + after


def process_recipe(path: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Return (recipe's Typst-ready markdown, [(ingredient, title, slug), ...])."""
    with open(path, encoding="utf-8") as f:
        raw = f.read().replace("%20", " ")
    meta, body = extract_front_matter(raw)

    slug = slugify(path)
    blocks = split_blocks(body)
    blocks, title = tag_title(blocks, slug)
    blocks = apply_lead_image_layout(path, blocks)

    ingredients = [
        (ingredient.strip(), title, slug)
        for ingredient in meta.get("main_ingredients", "").split(",")
        if ingredient.strip() and title
    ]
    return "\n\n".join(blocks), ingredients


def typst_text_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("@", "\\@")


def build_ingredient_index(entries: dict[str, list[tuple[str, str]]]) -> str:
    if not entries:
        return ""

    lines = ["```{=typst}", "#pagebreak()", "= Ingrediëntenindex", ""]
    for ingredient in sorted(entries, key=str.casefold):
        lines.append(f"- *{typst_text_escape(ingredient)}*")
        for title, slug in entries[ingredient]:
            page_lookup = f'#context query(label("{slug}")).first().location().page()'
            lines.append(f"  - {typst_text_escape(title)} (p. {page_lookup})")
    lines.append("```")
    return "\n".join(lines)


def build_combined_markdown(files: list[str]) -> str:
    parts = []
    entries: dict[str, list[tuple[str, str]]] = {}
    for path in files:
        markdown, recipe_ingredients = process_recipe(path)
        parts.append(markdown)
        for ingredient, title, slug in recipe_ingredients:
            entries.setdefault(ingredient, []).append((title, slug))

    pagebreak = "```{=typst}\n#pagebreak()\n```"
    combined = pagebreak + "\n\n" + ("\n\n" + pagebreak + "\n\n").join(parts)

    index = build_ingredient_index(entries)
    if index:
        combined += "\n\n" + index
    return combined


def main() -> None:
    recipes_dir, output_path = sys.argv[1], sys.argv[2]
    files = collect_recipes(recipes_dir)
    if not files:
        raise SystemExit(f"No recipe files found under {recipes_dir}")

    combined = build_combined_markdown(files)
    resource_path = ":".join(sorted({os.path.dirname(f) for f in files}))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as tmp:
        tmp.write(combined)
        combined_path = tmp.name

    header_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_header.typ")

    try:
        subprocess.run(
            [
                "pandoc",
                combined_path,
                "--pdf-engine=typst",
                f"--resource-path={resource_path}",
                f"--include-in-header={header_path}",
                "--metadata",
                "title=Receptenboek",
                "--metadata",
                "subtitle=Een verzameling van recepten",
                "--metadata",
                "author=Erika van den Heuvel & Rik Huygen",
                "--metadata",
                "lang=nl",
                "--metadata",
                "papersize=a4",
                "--metadata",
                "page-numbering=1",
                "--toc",
                "--toc-depth=1",
                "-o",
                output_path,
            ],
            check=True,
        )
    finally:
        os.remove(combined_path)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
