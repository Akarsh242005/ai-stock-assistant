import sys

html_file = r"c:\Users\Akarsh Sharma\Downloads\files\stockvision-dashboard.html"
with open(html_file, "r", encoding="utf-8") as f:
    text = f.read()

sections = text.split("// ════════════════════════════════════════════════")
for i, s in enumerate(sections):
    print(f"[{i}] {s[:60].strip()}")
