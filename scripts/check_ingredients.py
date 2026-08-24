"""Check that main_ingredients spellings are reused consistently across recipes.

The ingredient index in the PDF groups entries by exact string match (see
CLAUDE.md), so a recipe that spells an ingredient differently from the
rest -- for example "spekjes" instead of "spek" -- creates a silent
duplicate entry instead of joining the existing one. This script flags
name pairs that are similar but not identical, so the mismatch can be
fixed before the PDF is built.

Usage: python3 scripts/check_ingredients.py [recipes_dir]
"""

import difflib
import sys

from build_pdf import collect_recipes, extract_front_matter

SIMILARITY_THRESHOLD = 0.75


def collect_ingredient_names(files: list[str]) -> dict[str, list[str]]:
    """Return {ingredient name: [recipe paths that use it]}."""
    names: dict[str, list[str]] = {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        meta, _ = extract_front_matter(raw)
        for ingredient in meta.get("main_ingredients", "").split(","):
            ingredient = ingredient.strip()
            if ingredient:
                names.setdefault(ingredient, []).append(path)
    return names


def find_near_duplicates(names: list[str]) -> list[tuple[str, str, float]]:
    """Return (name, name, similarity) for distinct names that are close but not identical.

    A name that is a substring of another (for example "spek" inside
    "spekjes") is flagged outright, since that pattern is a common source
    of duplicate index entries: a singular versus a diminutive or plural
    form. Any other pair is flagged only above SIMILARITY_THRESHOLD, to
    catch plain typos without flagging unrelated short ingredient names.
    """
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            a_fold, b_fold = a.casefold(), b.casefold()
            if a_fold == b_fold:
                continue
            if a_fold in b_fold or b_fold in a_fold:
                pairs.append((a, b, 1.0))
                continue
            ratio = difflib.SequenceMatcher(None, a_fold, b_fold).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                pairs.append((a, b, ratio))
    return pairs


def main() -> None:
    recipes_dir = sys.argv[1] if len(sys.argv) > 1 else "docs/recepten"
    files = collect_recipes(recipes_dir)
    names = collect_ingredient_names(files)

    duplicates = find_near_duplicates(sorted(names))
    if not duplicates:
        print(f"No near-duplicate ingredient names found ({len(names)} distinct names checked).")
        return

    print("Possible inconsistent ingredient spellings:")
    for a, b, ratio in sorted(duplicates, key=lambda pair: -pair[2]):
        print(f'  "{a}" ({len(names[a])}x) vs "{b}" ({len(names[b])}x)')
    raise SystemExit(1)


if __name__ == "__main__":
    main()
