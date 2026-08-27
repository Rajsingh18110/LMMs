with open("lmms/gui/core/main_window.py", "r") as f:
    lines = f.readlines()

# Extract lines 411 to 498 (0-indexed: 410 to 498)
methods = lines[410:499]

# Delete them from the original location
del lines[410:499]

# Insert them before the end of the file (or at line 600, just as another method of MainWindow)
# Let's find def toggle_dock (which is at line 582 currently, so it will shift up by 89 lines)
# Let's just find the end of the file or insert it at a safe spot inside MainWindow.
# We will insert it at line 600 in the shifted list. Or just after toggle_dock.

insert_idx = 0
for i, line in enumerate(lines):
    if "def toggle_dock" in line:
        insert_idx = i - 1
        break

if insert_idx > 0:
    lines[insert_idx:insert_idx] = methods
else:
    # Just append at the end of the class? No, end of file is outside the class.
    # We can just put it at the end of the file as long as it's indented correctly.
    # Actually, we can find the class end.
    pass

with open("lmms/gui/core/main_window.py", "w") as f:
    f.writelines(lines)
