import sys
import os
from streamlit.web import cli as stcli

if __name__ == "__main__":
    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    sys.argv = [
        "streamlit",
        "run",
        main_path,
        "--server.port=8501",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
    sys.exit(stcli.main())
