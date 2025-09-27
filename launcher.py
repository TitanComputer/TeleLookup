import sys
import os
import time
import tempfile
from streamlit.web import cli as stcli


def close_splash():
    """Close Nuitka splash screen if running in onefile mode"""
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(),
            "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
        )
        if os.path.exists(splash_filename):
            try:
                os.unlink(splash_filename)
            except OSError:
                pass


if __name__ == "__main__":

    # (اختیاری) کمی تأخیر بدی تا مطمئن بشی استریم‌لیت بالا میاد
    time.sleep(5)

    # بستن اسپلش
    close_splash()

    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    sys.argv = [
        "streamlit",
        "run",
        main_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
