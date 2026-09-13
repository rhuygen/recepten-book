# De Website genereren en publiceren

```
$ uv run mkdocs build
$ uv run python3 scripts/build_pdf.py docs/recepten site/pdf/receptenboek.pdf
```

```
$ git add .
$ git commit -m "Update receptenboek website"
$ git push
```
