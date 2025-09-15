import streamlit as st
import pandas as pd
import os
import signal
import time
import re
import tkinter as tk
from tkinter import filedialog


class TeleLookupApp:
    def __init__(self, idle_timeout=300, chunk_size=10000):
        self.idle_timeout = idle_timeout
        self.chunk_size = chunk_size

        if "file_path" not in st.session_state:
            st.session_state["file_path"] = ""
        if "results" not in st.session_state:
            st.session_state["results"] = pd.DataFrame()
        if "search_clicked" not in st.session_state:
            st.session_state["search_clicked"] = False
        if "last_action" not in st.session_state:
            st.session_state["last_action"] = time.time()

    # ---------- utility ----------
    def update_last_action(self):
        st.session_state["last_action"] = time.time()

    def shutdown(self):
        os.kill(os.getpid(), signal.SIGTERM)

    # ---------- data handling ----------
    def parse_line_fast(self, line):
        try:
            id_match = re.search(r"'id'\s*:\s*([0-9]+)", line)
            user_match = re.search(r"'username'\s*:\s*'([^']*)'", line)
            phone_match = re.search(r"'phone'\s*:\s*'([^']*)'", line)
            if not (id_match and user_match and phone_match):
                return None
            return {"id": id_match.group(1), "username": user_match.group(1), "phone": phone_match.group(1)}
        except Exception:
            return None

    def matches(self, parsed, id_query, user_query, phone_query):
        match = True
        if id_query and id_query not in parsed["id"]:
            match = False
        if user_query and user_query.lower() not in parsed["username"].lower():
            match = False
        if phone_query and phone_query not in parsed["phone"]:
            match = False
        return match

    # ---------- search ----------
    def search_file(self, id_query="", user_query="", phone_query=""):
        file_path = st.session_state.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            st.warning("No file loaded.")
            return
        start_time = time.time()

        results_list = []
        total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8", errors="ignore")) - 1
        progress_bar = st.progress(0)
        percent_text = st.empty()
        elapsed_text = st.empty()

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:

            next(f)  # skip first line
            chunk = []
            for idx, line in enumerate(f, start=1):
                chunk.append(line.strip())
                if len(chunk) >= self.chunk_size:
                    for l in chunk:
                        parsed = self.parse_line_fast(l)
                        if parsed and self.matches(parsed, id_query, user_query, phone_query):
                            results_list.append(parsed)
                    chunk = []
                    percent = min(int(idx / total_lines * 100), 100)
                    progress_bar.progress(idx / total_lines)
                    percent_text.text(f"Progress: {percent}%")
                    elapsed = time.time() - start_time
                    elapsed_text.text(f"Elapsed time: {elapsed:.1f} sec")

            percent_text = st.empty()

            # remaining lines
            for l in chunk:
                parsed = self.parse_line_fast(l)
                if parsed and self.matches(parsed, id_query, user_query, phone_query):
                    results_list.append(parsed)

        progress_bar.progress(1.0)
        progress_bar.empty()

        if results_list:
            df = pd.DataFrame.from_records(results_list).drop_duplicates()
            st.session_state["results"] = df
        else:
            st.session_state["results"] = pd.DataFrame()
        st.session_state["search_clicked"] = True
        self.update_last_action()

    def reset(self):
        st.session_state["results"] = pd.DataFrame()
        st.session_state["search_clicked"] = False
        self.update_last_action()

    # ---------- idle ----------
    def check_idle_timeout(self):
        if time.time() - st.session_state.get("last_action", time.time()) > self.idle_timeout:
            st.warning("Idle timeout reached. Closing app...")
            self.shutdown()

    # ---------- UI ----------
    def browse_file(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(title="Select TeleDB File", filetypes=[("Text files", "*.txt")])
        root.destroy()
        return file_path

    def run(self):
        st.set_page_config(page_title="TeleLookup", layout="wide")
        self.check_idle_timeout()

        st.title("📂 TeleLookup")

        # --- File selection ---
        col1, col2 = st.columns([4, 1])
        with col1:
            file_path_display = st.text_input(
                "Selected File", value=st.session_state.get("file_path", ""), disabled=True
            )
        with col2:
            if st.button("Browse"):
                selected_path = self.browse_file()
                if selected_path and os.path.exists(selected_path):
                    st.session_state["file_path"] = selected_path
                    st.success("File ready for searching")
                    self.update_last_action()
                else:
                    st.warning("No file selected or file does not exist.")

        # --- Search UI ---
        if st.session_state["file_path"]:
            left_col, right_col = st.columns([3, 1])

            # compact input fields
            with left_col:
                id_query = st.text_input("ID", value="", key="id_search", max_chars=20)
                user_query = st.text_input("Username", value="", key="user_search", max_chars=20)
                phone_query = st.text_input("Phone", value="", key="phone_search", max_chars=20)

            # buttons aligned vertically, compact
            with right_col:
                st.markdown("<div style='display:flex; flex-direction:column; gap:5px;'>", unsafe_allow_html=True)
                if st.button("Search"):
                    self.search_file(id_query, user_query, phone_query)
                if st.button("Reset"):
                    self.reset()
                if st.button("Exit"):
                    st.info("Shutting down server...")
                    self.shutdown()
                st.markdown("</div>", unsafe_allow_html=True)

            results = st.session_state.get("results", pd.DataFrame())
            if st.session_state.get("search_clicked", False):
                if results.empty:
                    st.info("No results found")
                else:
                    st.subheader("Search Results")
                    st.dataframe(results, use_container_width=True)


if __name__ == "__main__":
    app = TeleLookupApp()
    app.run()
