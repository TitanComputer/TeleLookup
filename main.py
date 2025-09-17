import streamlit as st
import pandas as pd
import os
import signal
import time
import re
import tkinter as tk
from tkinter import filedialog


class TeleLookupApp:
    def __init__(self, idle_timeout=300, chunk_size=1000000):
        self.idle_timeout = idle_timeout
        self.chunk_size = chunk_size
        self.check_idle_timeout()

        if "file_path" not in st.session_state:
            st.session_state["file_path"] = ""
        if "results" not in st.session_state:
            st.session_state["results"] = pd.DataFrame()
        if "search_clicked" not in st.session_state:
            st.session_state["search_clicked"] = False
        if "last_action" not in st.session_state:
            st.session_state["last_action"] = time.time()
        if "show_search_ui" not in st.session_state:
            st.session_state["show_search_ui"] = False

    # ---------- utility ----------
    def update_last_action(self):
        st.session_state["last_action"] = time.time()

    def shutdown(self):
        os.kill(os.getpid(), signal.SIGTERM)

    # ---------- data handling ----------
    def parse_line_fast(self, line):
        try:
            # سریع‌تر از regex
            id_pos = line.find("'id'")
            user_pos = line.find("'username'")
            phone_pos = line.find("'phone'")

            if id_pos == -1 or user_pos == -1 or phone_pos == -1:
                return None

            # استخراج ID
            id_start = line.find(":", id_pos) + 1
            id_end = line.find(",", id_start)
            user_start = line.find("'", user_pos + 10) + 1
            user_end = line.find("'", user_start)
            phone_start = line.find("'", phone_pos + 9) + 1
            phone_end = line.find("'", phone_start)

            return {
                "id": line[id_start:id_end].strip(),
                "username": line[user_start:user_end],
                "phone": line[phone_start:phone_end],
            }
        except:
            return None

    def matches(self, parsed, id_query, user_query, phone_query):
        if id_query and id_query not in parsed["id"]:
            return False
        if user_query and user_query.lower() not in parsed["username"].lower():
            return False
        if phone_query and phone_query not in parsed["phone"]:
            return False
        return True

    # ---------- search ----------
    def search_file_streaming(self, id_query="", user_query="", phone_query="", results_placeholder=None):
        file_path = st.session_state.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            st.warning("No file loaded.")
            return

        total_start = time.time()
        results_list = []

        # placeholders
        progress_bar = st.progress(0)
        percent_text = st.empty()
        elapsed_text = st.empty()

        # ---------- count total lines (only first time) ----------
        t0 = time.time()
        if "total_lines" not in st.session_state or st.session_state.get("file_path_cached") != file_path:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                total_lines = sum(1 for _ in f) - 1
            st.session_state["total_lines"] = total_lines
            st.session_state["file_path_cached"] = file_path
            print(f"[TIMING] Counting lines took {time.time() - t0:.2f} sec (total lines: {total_lines})")
        else:
            total_lines = st.session_state["total_lines"]
            print(f"[CACHE] Using cached line count: {total_lines}")

        # ---------- read + search ----------
        parse_time = 0
        match_time = 0
        ui_time = 0
        t1 = time.time()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            next(f)  # skip first line
            chunk = []
            for idx, line in enumerate(f, start=1):
                chunk.append(line.strip())
                if len(chunk) >= self.chunk_size:
                    t_chunk = time.time()
                    for l in chunk:
                        t0 = time.time()
                        parsed = self.parse_line_fast(l)
                        parse_time += time.time() - t0

                        if parsed:
                            t1 = time.time()
                            if self.matches(parsed, id_query, user_query, phone_query):
                                results_list.append(parsed)
                            match_time += time.time() - t1
                    chunk = []

                    # update UI
                    t2 = time.time()
                    percent = min(int(idx / total_lines * 100), 100)
                    percent_text.text(f"Progress: {percent}%")
                    elapsed_text.text(f"Elapsed: {time.time()-total_start:.1f}s")
                    if results_list:
                        df = pd.DataFrame.from_records(results_list).drop_duplicates()
                        results_placeholder.dataframe(df, width="stretch")
                    progress_bar.progress(idx / total_lines)
                    ui_time += time.time() - t2

            print(f"[DETAIL] Parsing took {parse_time:.2f} sec")
            print(f"[DETAIL] Matching took {match_time:.2f} sec")
            print(f"[DETAIL] UI updates took {ui_time:.2f} sec")

            # remaining lines
            for l in chunk:
                parsed = self.parse_line_fast(l)
                if parsed and self.matches(parsed, id_query, user_query, phone_query):
                    results_list.append(parsed)
        print(f"[TIMING] Reading + searching took {time.time() - t1:.2f} sec")

        # ---------- finalize ----------
        progress_bar.progress(1.0)
        percent_text.text("Progress: 100%")
        elapsed_text.text(f"Elapsed time: {time.time()-total_start:.1f} sec")

        if results_list:
            df = pd.DataFrame.from_records(results_list).drop_duplicates()
            st.session_state["results"] = df
            results_placeholder.dataframe(df, width="stretch")  # نهایی
        else:
            st.session_state["results"] = pd.DataFrame()
            results_placeholder.info("No results found")

        print(
            f"[TIMING] Total search took {time.time() - total_start:.2f} sec "
            f"(Count: {time.time()-t0:.2f}s, Processing: {time.time()-t1:.2f}s)"
        )

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
        file_path = filedialog.askopenfilename(
            title="Select TeleDB_light.txt File", filetypes=[("Text files", "*.txt")]
        )
        root.destroy()

        if not file_path:
            return None  # کاربر Cancel زد
        return file_path

    def run(self):
        st.set_page_config(page_title="TeleLookup", layout="wide")
        self.check_idle_timeout()

        st.title("📂 TeleLookup")

        # --- File selection ---
        col1, col2 = st.columns([4, 1])

        with col1:
            st.text_input("Selected File", value=st.session_state.get("file_path", ""), disabled=True)

        with col2:
            # فاصله برای هم‌تراز شدن با text_input
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

            browse_disabled = st.session_state.get("show_search_ui", False)
            if st.button("📁 Browse File", disabled=browse_disabled):
                selected_path = self.browse_file()

                # بررسی اینکه آیا فایل انتخاب شده
                if not selected_path:
                    st.error("❌ No file selected.")
                # بررسی اینکه فایل وجود داره
                elif not os.path.isfile(selected_path):
                    st.error("❌ File does not exist.")
                # بررسی اینکه نام فایل درست باشه
                elif os.path.basename(selected_path) != "TeleDB_light.txt":
                    st.error("❌ Invalid file selected. Please select 'TeleDB_light.txt'.")
                else:
                    # valid file: set session state and rerun to update UI
                    st.session_state["file_path"] = selected_path
                    st.session_state["show_search_ui"] = True
                    st.session_state["file_loaded"] = True
                    self.update_last_action()
                    st.rerun()

        # after rerun, show success message in this same column
        if st.session_state.get("file_loaded", False):
            st.success("✅ File loaded successfully!")

        # --- Search UI ---
        if st.session_state.get("show_search_ui", False):
            st.markdown("---")
            # 🔹 اول سرچ باکس‌ها
            left_col, right_col = st.columns([3, 1])

            with left_col:
                id_query = st.text_input("🔎 ID", value="", key="id_search", max_chars=20)
                user_query = st.text_input("👤 Username", value="", key="user_search", max_chars=40)
                phone_query = st.text_input("📞 Phone", value="", key="phone_search", max_chars=20)

            # 🔹 جای نمایش نتایج (قبل از دکمه‌ها بسازیم که همیشه آماده باشه)
            st.markdown("---")
            results_placeholder = st.empty()

            with right_col:
                # فاصله از بالا
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

                # سه ستون برای سه دکمه در یک ردیف
                btn1, btn2, btn3 = st.columns([1, 1, 1])

                search_clicked = False  # فلگ برای تشخیص کلیک سرچ

                with btn1:
                    if st.button("🚀 Search"):
                        search_clicked = True  # فقط فلگ رو تغییر میدیم

                with btn2:
                    if st.button("🔄 Reset"):
                        self.reset()
                        results_placeholder.empty()  # نتایج پاک بشه

                with btn3:
                    if st.button("❌ Exit"):
                        st.info("Shutting down server...")
                        self.shutdown()

                # 🔹 اجرای سرچ در یک سطر پایین‌تر از کل دکمه‌ها
                if search_clicked:
                    self.search_file_streaming(id_query, user_query, phone_query, results_placeholder)
        self.check_idle_timeout()


if __name__ == "__main__":
    app = TeleLookupApp()
    app.run()
