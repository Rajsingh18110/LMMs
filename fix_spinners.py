import re

with open("lmms/backend/main.py", "r") as f:
    code = f.read()

# Replace outer spinner with 'if True:' to keep indentation
code = code.replace(
    '                    with console.status("[dim]Preparing request...[/dim]", spinner="lmms_wave"):',
    '                    if True:'
)

# Change 'Waiting for model' to 'Loading model'
code = code.replace(
    'Waiting for model',
    'Loading model'
)

with open("lmms/backend/main.py", "w") as f:
    f.write(code)
