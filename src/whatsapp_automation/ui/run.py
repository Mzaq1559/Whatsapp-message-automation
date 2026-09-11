import os
import subprocess
import sys


def main():
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    subprocess.run(cmd, check=False)

if __name__ == "__main__":
    main()
