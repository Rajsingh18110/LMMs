import os
import sys
import subprocess

env = os.environ.copy()
PROJECT_ROOT = "/home/kali/Projects/LMMs"
env["PYTHONPATH"] = PROJECT_ROOT

engine_script = os.path.join(PROJECT_ROOT, "lmms", "lmmsengine", "main.py")
log_file = os.path.expanduser("~/.lmms/logs/server.log")
try:
    with open(log_file, "a") as f:
        print("Starting subprocess...", file=sys.stderr)
        p = subprocess.Popen([sys.executable, engine_script, "server"], env=env, stdout=f, stderr=f, start_new_session=True)
        print("Subprocess started with pid", p.pid, file=sys.stderr)
except Exception as e:
    print("Exception:", e, file=sys.stderr)
