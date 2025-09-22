import streamlit as st
import pandas as pd
import os
import signal
import time
import threading
import tkinter as tk
from tkinter import filedialog
import mmap

APP_VERSION = "1.0.0"

# ===== ایجاد shared_state در سطح global/script
if "shared_state" not in st.session_state:
    st.session_state["shared_state"] = {"last_action": time.time()}


# ===== watchdog function
def watchdog(shared_state, idle_timeout):
    while True:
        last_action = shared_state["last_action"]
        if time.time() - last_action > idle_timeout:
            print("No activity detected, shutting down...")
            os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(5)
        # print(last_action)


# ===== singleton shared state + watchdog thread
@st.cache_resource
def get_shared_state():
    shared_state = {"last_action": time.time()}

    # start watchdog thread only once per process
    threading.Thread(target=watchdog, args=(shared_state, 300), daemon=True).start()

    return shared_state


# ===== get shared state for this session
@st.fragment()
def cache_shared_state():
    global shared_state
    shared_state = get_shared_state()


# ===== fragment برای keep-alive
@st.fragment(run_every="2s")
def keep_alive_fragment():
    shared_state["last_action"] = time.time()


class TeleLookupApp:
    def __init__(self, idle_timeout=300, chunk_size=1000000):
        cache_shared_state()
        keep_alive_fragment()
        self.idle_timeout = idle_timeout
        self.chunk_size = chunk_size

        if "file_path" not in st.session_state:
            st.session_state["file_path"] = ""
        if "file_loaded" not in st.session_state:
            st.session_state["file_loaded"] = False
        if "results" not in st.session_state:
            st.session_state["results"] = pd.DataFrame()
        if "search_clicked" not in st.session_state:
            st.session_state["search_clicked"] = False
        if "last_action" not in st.session_state:
            st.session_state["last_action"] = time.time()
        if "show_search_ui" not in st.session_state:
            st.session_state["show_search_ui"] = False
        if "no_results_found" not in st.session_state:
            st.session_state["no_results_found"] = False

    # ---------- utility ----------
    def update_last_action(self):
        return
        st.session_state["last_action"] = time.time()

    def shutdown(self):
        os.kill(os.getpid(), signal.SIGTERM)

    def parse_line_fast(self, line: str):
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
        seen_ids = set()

        # placeholders
        progress_bar = st.progress(0)
        percent_text = st.empty()
        elapsed_text = st.empty()
        found_text = st.empty()

        # ---------- count total lines ----------
        def count_lines_fast(filename):
            with open(filename, "rb") as f:
                return sum(buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b""))

        t_count_start = time.time()
        if "total_lines" not in st.session_state or st.session_state.get("file_path_cached") != file_path:
            total_lines = count_lines_fast(file_path)
            st.session_state["total_lines"] = total_lines
            st.session_state["file_path_cached"] = file_path
            print(f"[TIMING] Counting lines took {time.time() - t_count_start:.2f} sec (total lines: {total_lines})")
        else:
            total_lines = st.session_state["total_lines"]
            print(f"[CACHE] Using cached line count: {total_lines}")

        # prepare search terms
        id_q = id_query.strip() if id_query else None
        user_q = user_query.lower().strip() if user_query else None
        phone_q = phone_query.strip() if phone_query else None

        # ---------- read + search ----------
        parse_time = match_time = ui_time = df_time = dedup_time = 0.0
        io_time = 0.0
        t_proc_start = time.time()

        ui_update_interval = 0.5
        last_ui_update = 0.0

        with open(file_path, "r", encoding="utf-8", errors="ignore", buffering=16 * 1024 * 1024) as f:
            next(f)  # skip header
        with open(file_path, "rb") as fbin:
            with mmap.mmap(fbin.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                chunk = []
                for idx, raw_line in enumerate(iter(mm.readline, b""), start=1):
                    line = raw_line.decode("utf-8", errors="ignore")
                    chunk.append(line)

                    if len(chunk) >= self.chunk_size:
                        append = results_list.append
                        add = seen_ids.add
                        for l in chunk:
                            parsed = self.parse_line_fast(l)
                            if parsed:
                                username_lower = parsed["username"].lower()
                                if id_q and id_q not in parsed["id"]:
                                    continue
                                if user_q and user_q not in username_lower:
                                    continue
                                if phone_q and phone_q not in parsed["phone"]:
                                    continue
                                pid = parsed["id"]
                                if pid not in seen_ids:
                                    add(pid)
                                    append(parsed)
                        chunk = []

                        # --- UI updates ---
                        now = time.time()
                        if now - last_ui_update >= ui_update_interval:
                            percent = min(int(idx / total_lines * 100), 100)
                            found_count = len(results_list)
                            percent_text.text(f"Progress: {percent}%")
                            elapsed_text.text(f"Elapsed: {time.time()-total_start:.1f}s")
                            found_text.text(f"Found: {found_count}")
                            if results_list:
                                df = pd.DataFrame.from_records(results_list)
                                df.index = range(1, len(df) + 1)
                                results_placeholder.dataframe(df, width="stretch")
                            progress_bar.progress(idx / total_lines)
                            last_ui_update = now

                # remaining lines
                for l in chunk:
                    append = results_list.append
                    add = seen_ids.add
                    parsed = self.parse_line_fast(l)
                    if parsed:
                        username_lower = parsed["username"].lower()
                        if id_q and id_q not in parsed["id"]:
                            continue
                        if user_q and user_q not in username_lower:
                            continue
                        if phone_q and phone_q not in parsed["phone"]:
                            continue
                        pid = parsed["id"]
                        if pid not in seen_ids:
                            add(pid)
                            append(parsed)

        t_proc = time.time() - t_proc_start

        # finalize
        progress_bar.progress(1.0)
        percent_text.text("Progress: 100%")
        elapsed_text.text(f"Elapsed time: {time.time()-total_start:.1f} sec")
        found_text.text(f"Found: {found_count}")

        if results_list:
            t_df = time.time()
            df = pd.DataFrame.from_records(results_list)
            df.index = range(1, len(df) + 1)
            df_time += time.time() - t_df
            # ذخیره در session_state (تا بعد از rerun هم بماند)
            st.session_state["results"] = df
            st.session_state["no_results_found"] = False
            results_placeholder.dataframe(df, width="stretch")
        else:
            # هیچ نتیجه‌ای پیدا نشده
            st.session_state["results"] = pd.DataFrame()
            st.session_state["no_results_found"] = True
            results_placeholder.info("No results found")

        # timings
        print(f"[DETAIL] I/O read took {io_time:.2f} sec")
        print(f"[DETAIL] Parsing took {parse_time:.2f} sec")
        print(f"[DETAIL] Matching took {match_time:.2f} sec")
        print(f"[DETAIL] Dedup check took {dedup_time:.2f} sec")
        print(f"[DETAIL] DataFrame convert took {df_time:.2f} sec")
        print(f"[DETAIL] UI updates took {ui_time:.2f} sec")
        print(f"[TIMING] Reading + searching took {t_proc:.2f} sec")
        print(
            f"[TIMING] Total search took {time.time() - total_start:.2f} sec "
            f"(Count: {time.time()-t_count_start:.2f}s, Processing: {t_proc:.2f}s)"
        )

        st.session_state["search_clicked"] = False
        st.session_state["final_results"] = st.session_state["results"]
        st.session_state["final_progress"] = 100
        st.session_state["final_elapsed"] = f"Elapsed time: {time.time()-total_start:.1f} sec"
        st.session_state["final_found"] = f"Found: {len(results_list)}"
        st.rerun()
        self.update_last_action()

    def reset(self):
        st.session_state["results"] = pd.DataFrame()
        st.session_state["search_clicked"] = False
        st.session_state["no_results_found"] = False
        st.session_state.pop("final_results", None)
        st.session_state.pop("final_elapsed", None)
        st.session_state.pop("final_found", None)

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
        st.set_page_config(page_title=f"TeleLookup v{APP_VERSION}", layout="wide")
        header = st.container()
        with header:
            st.title(f"📂 TeleLookup v{APP_VERSION}")

        # --- File selection ---
        if not st.session_state.get("file_loaded", False):
            st.info("Please select the 'TeleDB_light.txt' file to proceed.")
            col1, col2 = st.columns([4, 1])

            with col1:
                st.text_input(
                    "Selected File", value=st.session_state.get("file_path", ""), disabled=True, key="file_input"
                )

            with col2:
                # فاصله برای هم‌تراز شدن با text_input
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)

                if st.button(
                    "📁 Browse File", disabled=st.session_state.get("show_search_ui", False), key="browse_btn"
                ):

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
            st.success("✅ TeleDB_light.txt File loaded successfully!")

        # --- Search UI ---
        if st.session_state.get("show_search_ui", False):
            st.markdown("---")
            # 🔹 اول سرچ باکس‌ها
            left_col, right_col = st.columns([3, 1])

            with left_col:
                id_query = st.text_input(
                    "🔎 ID",
                    value="",
                    key="id_search",
                    max_chars=20,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial Telegram unique ID (e.g. 12345678)",
                )
                user_query = st.text_input(
                    "👤 Username",
                    value="",
                    key="user_search",
                    max_chars=40,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial Telegram username (e.g. johndoe)",
                )
                phone_query = st.text_input(
                    "📞 Phone",
                    value="",
                    key="phone_search",
                    max_chars=20,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial phone number. Format: 989xxxxxxxxx",
                )

            # 🔹 جای نمایش نتایج (قبل از دکمه‌ها بسازیم که همیشه آماده باشه)
            st.markdown("---")
            results_placeholder = st.empty()

            if not st.session_state["results"].empty:
                results_placeholder.dataframe(st.session_state["results"], width="stretch")
            elif st.session_state.get("no_results_found", False):
                # اگر سرچ تموم شد ولی هیچ نتیجه‌ای نبود
                results_placeholder.info("No results found")
            # در غیر این صورت چیزی نمایش داده نمیشه (شروع سرچ جدول خالی خواهد بود)

            with right_col:
                # فاصله از بالا
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

                # سه ستون برای سه دکمه در یک ردیف
                btn1, btn2, btn3 = st.columns([1, 1, 1])

                # st.session_state["search_clicked"] = False  # فلگ برای تشخیص کلیک سرچ
                with btn1:
                    if st.button("🚀 Search"):
                        # پاک کردن نتایج قبلی بلافاصله
                        st.session_state["results"] = pd.DataFrame()
                        st.session_state["no_results_found"] = False
                        # شروع سرچ
                        st.session_state["search_clicked"] = True
                        # ری‌ران تا disabled شدن اینپوت‌ها و وضعیت دکمه‌ها اعمال بشه
                        st.rerun()

                with btn2:
                    if st.button("🔄 Reset", disabled=st.session_state["search_clicked"]):
                        self.reset()
                        results_placeholder.empty()

                with btn3:
                    if st.button("❌ Exit", disabled=st.session_state["search_clicked"]):
                        st.info("Shutting down server...")
                        self.shutdown()

                # 🔹 اجرای سرچ در یک سطر پایین‌تر از کل دکمه‌ها
                if st.session_state["search_clicked"]:
                    self.search_file_streaming(id_query, user_query, phone_query, results_placeholder)

                if "final_results" in st.session_state:
                    st.progress(1.0)
                    st.write("Progress: 100%")
                    st.write(st.session_state["final_elapsed"])
                    st.write(st.session_state["final_found"])


if __name__ == "__main__":
    app = TeleLookupApp()
    app.run()
