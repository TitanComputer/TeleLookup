import sys
import os
import time
import tempfile
import socket
import psutil
from tkinter import messagebox, Tk
from streamlit.web import cli as stcli


def close_splash():
    """Close Nuitka splash screen if running in onefile mode"""
    if "NUITKA_ONEFILE_PARENT" in os.environ:
        splash_filename = os.path.join(
            tempfile.gettempdir(), "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"])
        )
        if os.path.exists(splash_filename):
            try:
                os.unlink(splash_filename)
            except OSError:
                pass


def find_free_port(start_port=8501, max_tries=50):
    """Find the first free port starting from start_port"""
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found in range")


def check_and_kill_process(process_name):
    """Check if one or more processes are running and ask user to terminate them all"""
    matching_procs = [
        proc
        for proc in psutil.process_iter(attrs=["pid", "name"])
        if proc.info["name"] and proc.info["name"].lower() == process_name.lower()
    ]

    if not matching_procs:
        return True  # No process found, safe to continue

    # Create a temporary Tkinter root (hidden)
    root = Tk()
    root.withdraw()

    response = messagebox.askyesno(
        "Process Running",
        f"{process_name} is already running.\nDo you want to terminate it?",
    )

    root.destroy()

    if response:
        errors = []
        for proc in matching_procs:
            try:
                proc.kill()
            except Exception as e:
                errors.append(f"PID {proc.pid}: {e}")

        if errors:
            messagebox.showerror("Error", f"Failed to terminate some processes:\n" + "\n".join(errors))
            return False
        return True
    else:
        return False


if __name__ == "__main__":

    # Small delay to ensure Streamlit setup
    time.sleep(5)

    # Close splash if running with Nuitka
    close_splash()

    # Find a free port starting from 8501
    free_port = find_free_port(8501)

    # Check TeleLookup.exe process
    if not check_and_kill_process("TeleLookup.exe"):
        sys.exit(1)

    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    sys.argv = [
        "streamlit",
        "run",
        main_path,
        "--global.developmentMode=false",
        f"--server.port={free_port}",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
