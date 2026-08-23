"""Render all recipes straight from the Markdown source into one PDF.

This bypasses the MkDocs website build entirely and calls Pandoc, with
Typst as the PDF engine, directly on the recipe files under
src/recepten/. Typst gives proper page-break and figure control, which a
browser-based, CSS-driven PDF pipeline could not (see CLAUDE.md).

For a recipe whose first block is a standalone image, the PDF places
that image beside the ingredients instead of full-width, mirroring the
"float right" look of the website (see src/stylesheets/extra.css). Typst
has no CSS-style text reflow around a floating image, so this is a fixed
two-column layout instead: everything between the image and the first
heading-and-list pair (the title, and any intro text) stays full-width,
and the image is placed beside that heading-and-list pair itself.

Usage: python3 scripts/build_pdf.py <recipes_dir> <output_pdf_path>
"""

import glob
import os
import re
import subprocess
import sys
import tempfile

IMAGE_RE = re.compile(r"^!\[[^\]]*\]\(([^)]*)\)$")


def collect_recipes(recipes_dir: str) -> list[str]:
    categories = sorted(
        d for d in os.listdir(recipes_dir) if os.path.isdir(os.path.join(recipes_dir, d)) and d != "Images"
    )
    files = []
    for category in categories:
        files.extend(sorted(glob.glob(os.path.join(recipes_dir, category, "*.md"))))
    return files


def split_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n+", text.strip()) if b.strip()]


def is_heading(block: str) -> bool:
    return block.startswith("#")


LIST_ITEM_RE = re.compile(r"^(-|\*|\+|\d+\.)\s")


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
        "#grid(columns: (1fr, 40%), gutter: 1.5em, align: top,\n"
        "  [\n"
        f"{pair_typst}\n"
        "  ],\n"
        f'  image("{image_literal}", width: 100%),\n'
        ")\n"
        "```"
    )


def apply_lead_image_layout(path: str, text: str) -> str:
    blocks = split_blocks(text)
    if not blocks:
        return text

    match = IMAGE_RE.match(blocks[0])
    if not match:
        return text

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
        return text

    before = rest[:pair_index]
    pair_blocks = rest[pair_index : pair_index + 2]
    after = rest[pair_index + 2 :]

    grid = lead_image_grid(image_path, "\n\n".join(pair_blocks))
    return "\n\n".join(before + [grid] + after)


def build_combined_markdown(files: list[str]) -> str:
    parts = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read().replace("%20", " ")
        parts.append(apply_lead_image_layout(path, text.strip()))
    pagebreak = "```{=typst}\n#pagebreak()\n```"
    return pagebreak + "\n\n" + ("\n\n" + pagebreak + "\n\n").join(parts)


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

    try:
        subprocess.run(
            [
                "pandoc",
                combined_path,
                "--pdf-engine=typst",
                f"--resource-path={resource_path}",
                "--metadata",
                "title=Receptenboek",
                "--metadata",
                "subtitle=Een verzameling van recepten",
                "--metadata",
                "author=Rik Huygen",
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
