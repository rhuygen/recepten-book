"""MkDocs hook: place a recipe's lead image beside its ingredients.

Mirrors scripts/build_pdf.py's two-column layout on the website. Runs on
every page's Markdown before MkDocs converts it to HTML, so no recipe
file needs any layout markup itself.

For a recipe whose first block is a standalone image, this moves that
image to sit beside the list under the first heading immediately
followed by a list (the ingredients, whatever that section happens to
be titled), wrapping the list and the image in a flex row, defined in
docs/stylesheets/extra.css. The heading itself stays full-width, right
above that row, and so does everything before it -- the title, any
intro text. A recipe with no such heading-and-list pair keeps its image
full-width, unchanged.

The image's column defaults to 30% of the page width. A recipe can set
its own width with a `|<width>` suffix on the image's alt text, for
example `![Erwtensoep|30%](../Images/erwtensoep.jpg)`, parsed by
scripts/lead_image.py and shared with the PDF build. The suffix is
stripped before it reaches the page.

`markdown="1"` on the wrapping <div> tags asks the `md_in_html`
extension (see mkdocs.yml) to keep treating their contents as Markdown,
since a bare raw-HTML block would otherwise pass through unprocessed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lead_image import find_heading_list_pair, parse_lead_image, split_blocks

DEFAULT_LEAD_IMAGE_WIDTH = "30%"


def on_page_markdown(markdown, page, config, files):
    blocks = split_blocks(markdown)
    parsed = parse_lead_image(blocks, page.file.src_path)
    if parsed is None:
        return markdown
    alt_text, ref, width = parsed
    if width is None:
        width = DEFAULT_LEAD_IMAGE_WIDTH

    image_block = f"![{alt_text}]({ref})"
    rest = blocks[1:]

    pair_index = find_heading_list_pair(rest)
    if pair_index is None:
        # No ingredients-shaped section to pair with; keep the image at
        # the top, full-width.
        return "\n\n".join([image_block] + rest)

    heading = rest[pair_index]
    list_block = rest[pair_index + 1]
    before = rest[:pair_index] + [heading]
    after = rest[pair_index + 2 :]

    row = (
        f'<div class="lead-image-row" markdown="1" style="--lead-image-width: {width}">\n\n'
        '<div class="lead-image-row-text" markdown="1">\n\n'
        + list_block
        + "\n\n</div>\n\n"
        + image_block
        + "\n\n</div>"
    )

    return "\n\n".join(before + [row] + after)
