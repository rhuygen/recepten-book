"""Add an ingredient to the main_ingredients front matter of every recipe that uses it.

Usage: python3 scripts/add_ingredient.py <ingredient_name> [recipes_dir]

A recipe is a match when its body -- everything below the front matter --
contains the ingredient name, case-insensitively, as a substring. Dutch
compounds an ingredient name directly into related words (for example
"komijn" inside "komijnzaad" or "komijnpoeder"), so a substring search
also catches those forms; it may also catch an unrelated word that
happens to contain the same letters, so check the printed list of
changed recipes against `git diff` before you commit.

A recipe that already lists the name is left untouched, so the command
is safe to run more than once.
"""

from __future__ import annotations

import sys

from build_pdf import collect_recipes, extract_front_matter


def add_to_front_matter(raw: str, name: str) -> str | None:
    """Return the updated file text, or None if `name` is already listed."""
    meta, body = extract_front_matter(raw)
    existing = [i.strip() for i in meta.get("main_ingredients", "").split(",") if i.strip()]
    if any(i.casefold() == name.casefold() for i in existing):
        return None

    meta["main_ingredients"] = ", ".join(existing + [name])
    front_matter = "---\n" + "\n".join(f"{key}: {value}" for key, value in meta.items()) + "\n---\n"
    separator = "" if body.startswith("\n") else "\n"
    return front_matter + separator + body


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 scripts/add_ingredient.py <ingredient_name> [recipes_dir]")
    name = sys.argv[1]
    recipes_dir = sys.argv[2] if len(sys.argv) > 2 else "src/recepten"

    changed = []
    for path in collect_recipes(recipes_dir):
        with open(path, encoding="utf-8") as f:
            raw = f.read()

        _, body = extract_front_matter(raw)
        if name.casefold() not in body.casefold():
            continue

        updated = add_to_front_matter(raw, name)
        if updated is None:
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        changed.append(path)

    if not changed:
        print(f'No recipe needed "{name}" added.')
        return

    print(f'Added "{name}" to main_ingredients in:')
    for path in changed:
        print(f"  {path}")


if __name__ == "__main__":
    main()
