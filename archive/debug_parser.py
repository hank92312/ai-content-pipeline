from bs4 import BeautifulSoup
import re

with open("facebook_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
buttons = soup.find_all(lambda t: getattr(t, 'name', '') == 'div' and t.get('role') == 'button')

with open("debug_out.txt", "w", encoding="utf-8") as out:
    out.write(f"Total div[role=button]: {len(buttons)}\n")
    for i, b in enumerate(buttons):
        text = b.get_text(separator=' ', strip=True)
        if '分享' in text or '發佈' in text or '發布' in text:
            out.write(f"[{i}] {text}\n")
            out.write(f"    Classes: {b.get('class')}\n")
            out.write(f"    Aria-label: {b.get('aria-label')}\n")
            out.write(f"    Inner elements: {len(list(b.children))}\n")
        
