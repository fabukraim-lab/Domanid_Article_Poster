"""Fix broken viewport tag from migration across all articles."""
import os, glob

for f in glob.glob("articles/*.html"):
    if "index.html" in f:
        continue
    with open(f, "r", encoding="utf-8") as fh:
        c = fh.read()

    # Fix pattern: broken <meta name="viewport" followed by canonical
    old = '<meta name="viewport"\n    <link rel="canonical" href="https://domanid.com/articles/'
    new = '<link rel="canonical" href="https://domanid.com/articles/'
    if old in c:
        c = c.replace(old, new)
        # Also clean up duplicate viewport
        c = c.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <meta name="viewport"',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        )
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(c)
        print(f"Fixed: {os.path.basename(f)}")

print("Done")
