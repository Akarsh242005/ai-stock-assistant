import sys

file_path = r"c:\Users\Akarsh Sharma\Downloads\files\stockvision-dashboard.html"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

def find_line(prefix, start_idx=0):
    for i in range(start_idx, len(lines)):
        if lines[i].strip().startswith(prefix):
            return i
    return -1

print("idx_live_data =", find_line("// LIVE DATA FETCH"))
print("idx_main_search =", find_line("// MAIN SEARCH FLOW"))
print("idx_render_dashboard =", find_line("// RENDER DASHBOARD"))
print("idx_chart_vision =", find_line("// CHART VISION AI"))
print("idx_ui_helpers =", find_line("// CHART / UI HELPERS"))
