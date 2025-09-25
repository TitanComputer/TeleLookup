import os
import sys
import subprocess

if __name__ == "__main__":
    main_path = os.path.join(os.path.dirname(__file__), "main.py")

    # اجرای Streamlit به صورت subprocess
    subprocess.run([sys.executable, "-m", "streamlit", "run", main_path])
