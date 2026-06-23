"""Add Google Search Console verification tag to all existing articles."""
import os, glob

tag = '<meta name="google-site-verification" content="t2WIFPydoP4ktZH7QapjKr8Qpv1R7_UpP77-7zlIYpo">'
count = 0
for f in glob.glob("articles/*.html"):
    if "index.html" in f:
        continue
    with open(f, "r", encoding="utf-8") as fh:
        c = fh.read()
    if tag in c:
        continue
    c = c.replace('<link rel="canonical"', tag + '\n    <link rel="canonical"')
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(c)
    count += 1
print(f"Added GSC verification to {count} articles")
