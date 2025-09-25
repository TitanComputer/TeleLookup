import os
import sys
from streamlit.web import cli as stcli

if __name__ == "__main__":
    # مسیر main.py نسبت به همین فایل launcher
    main_path = os.path.join(os.path.dirname(__file__), "main.py")

    sys.argv = ["streamlit", "run", main_path]
    sys.exit(stcli.main())
