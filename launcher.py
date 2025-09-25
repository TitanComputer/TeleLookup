import os
from streamlit.web import bootstrap

if __name__ == "__main__":
    # مسیر فایل اصلی برنامه
    main_path = os.path.join(os.path.dirname(__file__), "main.py")

    # اینجا تنظیمات سرور رو مستقیماً پاس می‌دی
    bootstrap.load_config_options(
        flag_options={
            "server.port": 8501,
            "server.enableCORS": False,
            "server.enableXsrfProtection": False,
            "global.developmentMode": False,  # کلید اصلی
        }
    )

    bootstrap.run(main_path, "", [], flag_options={})
