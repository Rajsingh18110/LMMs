import sys, os
import subprocess, shutil

print("PATH:", os.environ.get('PATH'))
print("shutil.which('zenity'):", shutil.which('zenity'))

try:
    result = subprocess.run(['zenity', '--version'], capture_output=True, text=True)
    print("Return code:", result.returncode)
    print("Stdout:", result.stdout.strip())
    print("Stderr:", result.stderr.strip())
except Exception as e:
    print("Exception:", e)
