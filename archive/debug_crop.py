from bs4 import BeautifulSoup
import json

with open("ig_crop_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
# Find all SVGs that might act as the crop ratio button.
# "Select crop", "選擇顯示比例", "設定顯示比例", "比例", "9:16", etc.
svgs = soup.find_all("svg")
with open("debug_crop_out.txt", "w", encoding="utf-8") as out:
    out.write(f"Total SVGs: {len(svgs)}\n")
    for i, s in enumerate(svgs):
        aria = s.get('aria-label') or s.get('alt') or ''
        if '比例' in aria or 'crop' in aria.lower() or '格式' in aria or '顯示' in aria or '9:16' in aria or '選擇' in aria:
            out.write(f"[{i}] SVG found! aria-label: {aria}\n")
            parent = s.find_parent("button")
            if parent:
                out.write(f"    Parent Button Classes: {parent.get('class')}\n")

    # Also find any spans with 9:16
    spans = soup.find_all(lambda t: getattr(t, 'name', '') in ['span', 'div'] and '9:16' in t.get_text())
    out.write(f"\nElements with 9:16: {len(spans)}\n")
    for sp in spans:
        out.write(f"    {sp.name} classes: {sp.get('class')}\n")

