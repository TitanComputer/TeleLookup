import os
import pandas as pd
import signal
import time
import threading
import tkinter as tk
from tkinter import filedialog
import mmap
import base64


def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def resource_path(relative_path):
    """Returns the absolute path to a file in the same directory as the script.
    This is used to find resources like images when the script is run from a
    different directory (e.g. as an executable)."""
    temp_dir = os.path.dirname(__file__)
    return os.path.join(temp_dir, relative_path)


# ---------- count total lines ----------
def count_lines_fast(filename):
    with open(filename, "rb") as f:
        return sum(buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b""))


# ---------- parse line ----------
def parse_line_fast(line: str):
    try:
        # یکبار scan از ابتدا تا انتها
        id_idx = line.find("'id':")
        user_idx = line.find("'username':")
        phone_idx = line.find("'phone':")

        if id_idx == -1 or user_idx == -1 or phone_idx == -1:
            return None

        # استخراج ID
        id_start = id_idx + 5
        id_end = line.find(",", id_start)

        # استخراج username
        user_start = line.find("'", user_idx + 11) + 1
        user_end = line.find("'", user_start)

        # استخراج phone
        phone_start = line.find("'", phone_idx + 9) + 1
        phone_end = line.find("'", phone_start)

        return {
            "id": line[id_start:id_end],
            "username": line[user_start:user_end],
            "phone": line[phone_start:phone_end],
        }
    except:
        return None


# ---------- process chunk ----------
def process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list):
    # آماده‌سازی queryها بیرون از حلقه
    id_q = id_q or None
    user_q = user_q.lower() if user_q else None
    phone_q = phone_q or None

    local_add = add
    local_append = append
    local_seen = seen_ids

    for line in chunk:
        parsed = parse_line(line)
        if not parsed:
            continue

        pid = parsed["id"]

        if id_q and id_q not in pid:
            continue
        if user_q and user_q not in parsed["username"].lower():
            continue
        if phone_q and phone_q not in parsed["phone"]:
            continue

        if pid not in local_seen:
            local_add(pid)
            local_append(parsed)
