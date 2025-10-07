# TeleLookup , A Telegram Database Search Web App

> ⚠️ **Note**  
> This application requires the original **TeleDB_light.txt** database (≈2.51 GB, 42,823,958 lines).  
> A small sample file (with fake data) is provided in this repository for testing purposes.  
> [Download sample TeleDB_light.txt](https://raw.githubusercontent.com/TitanComputer/TeleLookup/main/sample/TeleDB_light.txt)
> Please do **NOT** ask me to provide the original database file.  
>
> 🚨 **Disclaimer**  
> This project is created **for research and programming practice purposes only**.  
> Any misuse of this application is strictly prohibited.  

---

## 📖 Overview

This is a **Streamlit-based web application** that allows you to quickly search through a Telegram database dump file.  

You can:  
- Search for records in the Telegram database.  
- Reset or stop searches at any time.  

---
## 🚀 How it Works

1. The app loads the **TeleDB_light.txt** (or the provided sample) into memory.  
2. You can perform search queries directly from the Web UI.  
3. Results are displayed in a clean, interactive interface.  
4. Buttons are available to **reset**, **stop**, or **exit**.

---

## ✨ Features

- 🚀 **Fast Telegram Database Search** – Quickly search IDs, usernames, or phone numbers in large TeleDB_light files.  
- 🧠 **Streaming Results** – Displays matches as they are found without waiting for the entire search to finish.  
- 🛑 **Stop Functionality** – Allows you to stop an ongoing search safely.  
- 🔄 **Reset Functionality** – Clear search results and inputs to start fresh.  
- 🕒 **Idle Timeout Protection** – Automatically shuts down the app after inactivity to save resources.  
- 🎉 **User-Friendly GUI** – Simple, step-by-step interface for easy navigation and operation.  
- 📥 **Compiled Exe** - Downloadable `.exe` version (Windows only)


## 🖼️ Screenshots

<img width="1350" height="411" alt="Untitled4" src="https://github.com/user-attachments/assets/3d8f975c-6dad-4743-a9d8-87b669ede6c3" />


## 📥 Download

You can download the latest compiled `.exe` version from the [Releases](https://github.com/TitanComputer/TeleLookup/releases/latest) section.  
No need to install Python — just download and run.

### 🖥️ How to Use the GUI

1. **Launch the App**  
   - If running via executable, double-click **`TeleLookup.exe`**.  
   - If running via Streamlit, open a terminal and run:  
     ```bash
     streamlit run app.py
     ```

2. **Load the Database File**  
   - When prompted, click **📁 Browse File**.  
   - Select `TeleDB_light.txt` from your system (the main database).  
   - Once loaded, a success message will appear:  
     ✅ TeleDB_light.txt File loaded successfully!

3. **Search Records**  
   - Enter a query in any of the input fields:  
     - **ID** – full or partial Telegram ID  
     - **Username** – full or partial Telegram username  
     - **Phone** – full or partial phone number (format: 989xxxxxxxxx)  
   - Click **🚀 Search** to start.  
   - If needed, click **🛑 Stop** to halt the search at any time.

4. **View Results**  
   - Search results will appear in the results table.  
   - You can scroll, sort, and inspect the matches.  
   - If no results are found, an info message will indicate that.

5. **Additional Actions**  
   - **🔄 Reset** – clears current search results and inputs.  
   - **❤️ Donate** – opens the donation dialog with USDT wallet info.  
   - **❌ Exit** – shuts down the app safely.

6. **Inactivity Warning**  
   - If no activity occurs for more than the configured idle timeout (default 5 minutes),  
     the app will automatically shut down to free resources.

---

## 📦 Dependencies

- Python 3.11 or newer
- `Streamlit`
- Recommended: Create a virtual environment

Standard libraries only (os, re, etc.)

If you're modifying and running the script directly and use additional packages (like requests or tkinter), install them via:
```bash
pip install -r requirements.txt
```

## 📁 Project Structure

```bash
TeleLookup/
│
├── main.py                     # Main application entry point
├── launcher.py                 # Launcher script for Nuitka
├── core.py                     # Application core logic
├── README.md                   # Project documentation
├── assets/
│   ├── icon.png                # Project icon
│   └── donate.png              # Donate Picture
├── sample/
│   └── TeleDB_light.txt        # Sample database
└── requirements.txt            # Python dependencies
```
## 🎨 Icon Credit
The application icon used in this project is sourced from [Flaticon](https://www.flaticon.com/free-icons/search-file).

**Search icon** created by [Smashicons](https://www.flaticon.com/authors/smashicons) – [Flaticon](https://www.flaticon.com/)

## 🛠 Compiled with Nuitka and UPX
The executable was built using [`Nuitka`](https://nuitka.net/) and [`UPX`](https://github.com/upx/upx) for better performance and compactness, built automatically via GitHub Actions.

You can build the standalone executable using the following command:

```bash
.\venv\Scripts\python.exe -m nuitka --jobs=4 --enable-plugin=upx --upx-binary="YOUR PATH\upx.exe" --enable-plugin=multiprocessing --lto=yes --enable-plugin=tk-inter --disable-plugin=anti-bloat --windows-console-mode=disable --follow-imports --windows-icon-from-ico="assets/icon.png" --include-data-dir=assets=assets --include-data-files=main.py=main.py --include-data-dir="YOUR PATH\venv\Lib\site-packages\streamlit"=streamlit --include-package=streamlit --include-package=streamlit.runtime --include-package=streamlit.runtime.scriptrunner --include-module=core --no-deployment-flag=self-execution --onefile --onefile-windows-splash-screen-image=assets/icon.png --standalone --msvc=latest --assume-yes-for-downloads --output-filename=TeleLookup launcher.py
```

## 🚀 CI/CD

The GitHub Actions workflow builds the binary on every release and attaches it as an artifact.

## 🤝 Contributing
Pull requests are welcome.
If you have suggestions for improvements or new features, feel free to open an issue.

## ☕ Support
If you find this project useful and would like to support its development, consider donating:

<a href="http://www.coffeete.ir/Titan"><img width="500" height="140" alt="buymeacoffee" src="https://github.com/user-attachments/assets/8ddccb3e-2afc-4fd9-a782-89464ec7dead" /></a>

## 💰 USDT (Tether) – TRC20 Wallet Address:

```bash
TGoKk5zD3BMSGbmzHnD19m9YLpH5ZP8nQe
```
Thanks a lot for your support! 🙏
