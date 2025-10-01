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
                # Small delay to ensure Streamlit setup
                print("Closing splash screen...")
                time.sleep(5)
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


def _is_related(proc, current):
    """Return True if proc is ancestor or descendant of current process."""
    try:
        # check if proc is an ancestor of current
        p = current
        while True:
            parent = p.parent()
            if parent is None:
                break
            if parent.pid == proc.pid:
                return True
            p = parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    try:
        # check if proc is a descendant of current
        p = proc
        while True:
            parent = p.parent()
            if parent is None:
                break
            if parent.pid == current.pid:
                return True
            p = parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return False


def check_and_kill_process(process_name, debug=False):
    """
    Find other running instances of `process_name` that are NOT part of
    this instance's process tree and that started before this instance.
    Ask the user to terminate them all. Returns True if safe to continue.
    """
    current = psutil.Process(os.getpid())
    try:
        current_start = current.create_time()
    except Exception:
        current_start = time.time()

    candidates = []
    all_found = []

    for proc in psutil.process_iter(attrs=["pid", "name", "create_time"]):
        try:
            info = proc.info
            name = info.get("name")
            if not name or name.lower() != process_name.lower():
                continue

            pid = info.get("pid")
            create_time = info.get("create_time")
            all_found.append((pid, name, create_time))

            if pid == current.pid:
                continue

            # skip processes that are in the same process tree (ancestor/descendant)
            if _is_related(proc, current):
                continue

            # ensure proc started before current (use a tiny tolerance to avoid race)
            if create_time is None:
                try:
                    create_time = proc.create_time()
                except Exception:
                    create_time = 0

            if create_time >= (current_start - 0.1):
                # started at same time or after current -> likely part of this instance or not an "older" instance
                continue

            candidates.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if debug:
        print("All matching-name processes (pid, name, create_time):", all_found)
        print("Candidates to consider terminating (pid):", [p.pid for p in candidates])

    if not candidates:
        return True

    root = Tk()
    root.withdraw()
    response = messagebox.askyesno(
        "Process Running",
        f"{process_name} is already running.\nDo you want to terminate it and run a new instance?",
    )
    root.destroy()

    if not response:
        return False

    errors = []
    for proc in candidates:
        try:
            proc.kill()
        except Exception as e:
            errors.append(f"PID {proc.pid}: {e}")

    if errors:
        root = Tk()
        root.withdraw()
        messagebox.showerror("Error", "Failed to terminate some processes:\n" + "\n".join(errors))
        root.destroy()
        return False

    return True


if __name__ == "__main__":

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
