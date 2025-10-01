import streamlit as st
from core import *

APP_VERSION = "1.4.0"

# ===== initialize shared state
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


# ===== fragments for updating last_action
@st.fragment(run_every="2s")
def keep_alive_fragment():
    shared_state["last_action"] = time.time()


@st.fragment(run_every="5s")
def user_action_fragment(idle_timeout):
    now = time.time()
    if now - st.session_state.get("user_action", now) > idle_timeout:
        st.warning("You have been inactive for too long. Closing app...")
        print("User inactive for too long. Closing app...")
        time.sleep(1)  # allow UI to update
        os.kill(os.getpid(), signal.SIGTERM)


class TeleLookupApp:
    def __init__(self, idle_timeout=300, chunk_size=1000000):
        self.idle_timeout = idle_timeout
        self.chunk_size = chunk_size
        self.icon_path = resource_path(os.path.join("assets", "icon.png"))
        cache_shared_state()
        keep_alive_fragment()
        user_action_fragment(self.idle_timeout)

        if "file_path" not in st.session_state:
            st.session_state["file_path"] = ""
        if "file_loaded" not in st.session_state:
            st.session_state["file_loaded"] = False
        if "results" not in st.session_state:
            st.session_state["results"] = pd.DataFrame()
        if "search_clicked" not in st.session_state:
            st.session_state["search_clicked"] = False
        if "shutdown_clicked" not in st.session_state:
            st.session_state["shutdown_clicked"] = False
        if "last_action" not in st.session_state:
            st.session_state["last_action"] = time.time()
        if "show_search_ui" not in st.session_state:
            st.session_state["show_search_ui"] = False
        if "no_results_found" not in st.session_state:
            st.session_state["no_results_found"] = False
        if "stop_search" not in st.session_state:
            st.session_state["stop_search"] = False
        if "user_action" not in st.session_state:
            st.session_state["user_action"] = time.time()

    # ---------- utility ----------
    def update_user_action(self):
        st.session_state["user_action"] = time.time()

    def shutdown(self):
        time.sleep(1)  # allow UI to update
        os.kill(os.getpid(), signal.SIGTERM)

    # ---------- search ----------
    def search_file_streaming(self, id_query="", user_query="", phone_query="", results_placeholder=None):
        file_path = st.session_state.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            st.warning("No file loaded.")
            return

        if "total_start" not in st.session_state:
            st.session_state["total_start"] = time.time()

        total_start = st.session_state["total_start"]
        results_list = []
        seen_ids = set()

        # placeholders
        progress_bar = st.progress(0)
        percent_text = st.empty()
        elapsed_text = st.empty()
        found_text = st.empty()

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

        append = results_list.append
        add = seen_ids.add
        parse_line = parse_line_fast
        stopped = False
        with open(file_path, "rb") as fbin:
            with mmap.mmap(fbin.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                mm.readline()  # skip header
                chunk = []
                stop_search = st.session_state.get("stop_search", False)
                for idx, raw_line in enumerate(iter(mm.readline, b""), start=1):
                    if stop_search:
                        # flush current chunk to keep partial results
                        if chunk:
                            process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list)
                            chunk.clear()
                        stopped = True
                        print("[INFO] Search stopped by user at line", idx)
                        break
                    chunk.append(raw_line.decode("utf-8", errors="ignore"))
                    if len(chunk) >= self.chunk_size:
                        process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list)
                        chunk.clear()
                        # --- UI updates ---
                        # st.session_state["shared_state"]["last_action"] = time.time()
                        # print(f"[DEBUG] Processed {idx}/{total_lines} lines, found {len(results_list)} matches")
                        now = time.time()
                        if now - last_ui_update >= ui_update_interval:
                            percent = min(int(idx / total_lines * 100), 100)
                            percent_text.text(f"Progress: {percent}%")
                            elapsed_text.text(f"Elapsed: {time.time()-total_start:.1f}s")
                            found_text.text(f"Found: {len(results_list)}")
                            if results_list:
                                df = pd.DataFrame.from_records(results_list)
                                df.index = range(1, len(df) + 1)
                                results_placeholder.dataframe(df, width="stretch")
                                st.session_state["results"] = df
                                st.session_state["no_results_found"] = False
                            progress_bar.progress(idx / total_lines)
                            last_ui_update = now
                        # time.sleep(0)

                # if loop finished normally, process remaining chunk
                if not stopped and chunk:
                    process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list)
                    chunk.clear()

        t_proc = time.time() - t_proc_start

        if stopped:
            # if there are previous results in session, keep them and just inform user
            prev = st.session_state.get("results", pd.DataFrame())
            if prev.empty:
                st.session_state["results"] = pd.DataFrame()
                st.session_state["no_results_found"] = True

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
        self.update_user_action()
        st.rerun()

    def reset(self):
        st.session_state["results"] = pd.DataFrame()
        st.session_state["search_clicked"] = False
        st.session_state["no_results_found"] = False
        st.session_state["stop_search"] = False
        st.session_state.pop("final_results", None)
        st.session_state.pop("final_elapsed", None)
        st.session_state.pop("final_found", None)
        st.session_state.pop("total_start", None)

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
            return None  # user cancelled
        return file_path

    def run(self):
        st.set_page_config(page_title=f"TeleLookup v{APP_VERSION}", layout="wide", page_icon=self.icon_path)
        header = st.container()
        with header:
            col1, col2 = st.columns([1, 15])
            with col1:
                st.image(self.icon_path, width=96)
            with col2:
                st.title(f"TeleLookup v{APP_VERSION}")

        # --- File selection ---
        if not st.session_state.get("file_loaded", False):
            st.info("Please select the 'TeleDB_light.txt' file to proceed.")
            col1, col2 = st.columns([4, 1])

            with col1:
                st.text_input(
                    "Selected File", value=st.session_state.get("file_path", ""), disabled=True, key="file_input"
                )

            with col2:
                # add some space from top
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                searchbtn, exitbtn = st.columns([1, 1])

                with searchbtn:
                    if st.button(
                        "📁 Browse File", disabled=st.session_state.get("show_search_ui", False), key="browse_btn"
                    ):

                        selected_path = self.browse_file()

                        # check if file selected
                        if not selected_path:
                            st.error("❌ No file selected.")
                        # check if file exists
                        elif not os.path.isfile(selected_path):
                            st.error("❌ File does not exist.")
                        # check if file is TeleDB_light.txt
                        elif os.path.basename(selected_path) != "TeleDB_light.txt":
                            st.error("❌ Invalid file selected. Please select 'TeleDB_light.txt'.")
                        else:
                            # valid file: set session state and rerun to update UI
                            st.session_state["file_path"] = selected_path
                            st.session_state["show_search_ui"] = True
                            st.session_state["file_loaded"] = True
                            st.rerun()
                        self.update_user_action()

                with exitbtn:
                    if st.button("❌ Exit", disabled=st.session_state["search_clicked"]):
                        st.session_state["shutdown_clicked"] = True

                if st.session_state["shutdown_clicked"]:
                    st.info("Shutting down server...")
                    self.shutdown()

        # after rerun, show success message in this same column
        if st.session_state.get("file_loaded", False):
            st.success("✅ TeleDB_light.txt File loaded successfully!")
            self.update_user_action()

        # --- Search UI ---
        if st.session_state.get("show_search_ui", False):
            st.markdown("---")
            # split into two columns
            left_col, right_col = st.columns([3, 1])

            with left_col:
                id_query = st.text_input(
                    "🔎 ID",
                    value="",
                    key="id_search",
                    max_chars=20,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial Telegram unique ID (e.g. 12345678)",
                    on_change=self.update_user_action,
                )
                user_query = st.text_input(
                    "👤 Username",
                    value="",
                    key="user_search",
                    max_chars=40,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial Telegram username (e.g. johndoe)",
                    on_change=self.update_user_action,
                )
                phone_query = st.text_input(
                    "📞 Phone",
                    value="",
                    key="phone_search",
                    max_chars=20,
                    disabled=st.session_state["search_clicked"],
                    placeholder="Enter full or partial phone number. Format: 989xxxxxxxxx",
                    on_change=self.update_user_action,
                )

            # --- Results + Buttons ---
            st.markdown("---")
            results_placeholder = st.empty()

            if not st.session_state["results"].empty:
                results_placeholder.dataframe(st.session_state["results"], width="stretch")
            elif st.session_state.get("no_results_found", False):
                # if no results found in previous search, show message
                results_placeholder.info("No results found")
            # else: empty at start

            with right_col:
                # add some space from top
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

                # split into three columns
                btn1, btn2, btn3 = st.columns([1, 1, 1])

                with btn1:
                    if not st.session_state["search_clicked"]:
                        # search button
                        if st.button("🚀 Search"):
                            results_placeholder.empty()
                            st.session_state.pop("total_start", None)
                            st.session_state["results"] = pd.DataFrame()
                            st.session_state["no_results_found"] = False
                            st.session_state["stop_search"] = False
                            st.session_state["search_clicked"] = True
                            self.update_user_action()
                            st.rerun()
                    else:
                        # stop button
                        if st.button("🛑 Stop"):
                            self.update_user_action()
                            st.session_state["stop_search"] = True

                with btn2:
                    if st.button("🔄 Reset", disabled=st.session_state["search_clicked"]):
                        self.update_user_action()
                        self.reset()
                        results_placeholder.empty()

                with btn3:
                    if st.button("❌ Exit", disabled=st.session_state["search_clicked"]):
                        st.session_state["shutdown_clicked"] = True

                if st.session_state["shutdown_clicked"]:
                    st.info("Shutting down server...")
                    self.shutdown()

                # start search
                if st.session_state["search_clicked"]:
                    self.search_file_streaming(id_query, user_query, phone_query, results_placeholder)

                if st.session_state.get("stop_search", False):
                    elapsed = time.time() - st.session_state["total_start"]  # elapsed time
                    st.progress(min(st.session_state.get("final_progress", 0) / 100, 1.0))
                    st.write("Search stopped by user.")
                    st.write(f"Elapsed: {elapsed:.1f} sec")  # show elapsed time
                    st.write(f"Found so far: {len(st.session_state.get('results', []))}")
                else:
                    # if search finished normally, show final stats
                    if "final_results" in st.session_state:
                        st.progress(1.0)
                        st.write("Progress: 100%")
                        st.write(st.session_state["final_elapsed"])
                        st.write(st.session_state["final_found"])
        st.info(
            f"ℹ️ Note: If you remain inactive for more than {self.idle_timeout // 60} minutes, "
            "the app will automatically shut down due to inactivity."
        )


if __name__ == "__main__":
    app = TeleLookupApp()
    app.run()
