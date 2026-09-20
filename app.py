import sys
import os
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

# Ensure local directories are in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from i18n import Translator
from ui import MainWindow
from core import is_admin


CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"language": "en", "theme": "dark"}


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[-] Failed to save config: {e}")


def main():
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Bluetooth Tweaker Pro")
    app.setApplicationDisplayName("Bluetooth Tweaker Pro (Community Edition)")

    # Set default modern font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Load configuration & initialize translator
    config = load_config()
    translator = Translator.get_instance()
    initial_lang = config.get("language", "en")
    translator.set_locale(initial_lang)

    # Save language preference when changed
    def on_lang_changed(code: str):
        config["language"] = code
        save_config(config)

    translator.language_changed.connect(on_lang_changed)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
