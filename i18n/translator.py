import json
import os
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal


class Translator(QObject):
    """
    JSON-based internationalization (i18n) engine.
    Supports dynamic language switching at runtime with Qt signal notifications.
    """
    language_changed = pyqtSignal(str)

    _instance: Optional['Translator'] = None

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "vi": "Tiếng Việt",
        "zh": "简体中文",
        "ja": "日本語"
    }

    def __init__(self, locales_dir: Optional[str] = None):
        super().__init__()
        if locales_dir is None:
            # Default to locales directory relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.locales_dir = os.path.join(base_dir, "locales")
        else:
            self.locales_dir = locales_dir

        self.current_locale = "en"
        self.translations: Dict[str, Any] = {}
        self.fallback_translations: Dict[str, Any] = {}

        self._load_locale("en", is_fallback=True)
        self.set_locale("en")

    @classmethod
    def get_instance(cls) -> 'Translator':
        if cls._instance is None:
            cls._instance = Translator()
        return cls._instance

    def _load_locale(self, locale_code: str, is_fallback: bool = False) -> bool:
        file_path = os.path.join(self.locales_dir, f"{locale_code}.json")
        if not os.path.exists(file_path):
            print(f"[!] Warning: Locale file not found: {file_path}")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if is_fallback:
                    self.fallback_translations = data
                else:
                    self.translations = data
            return True
        except Exception as e:
            print(f"[-] Failed to load locale {locale_code}: {e}")
            return False

    def set_locale(self, locale_code: str) -> bool:
        if locale_code not in self.SUPPORTED_LANGUAGES:
            locale_code = "en"

        if not self._load_locale(locale_code, is_fallback=False):
            if locale_code != "en":
                self.current_locale = "en"
                self.translations = self.fallback_translations
                return False

        self.current_locale = locale_code
        self.language_changed.emit(locale_code)
        return True

    def get_locale(self) -> str:
        return self.current_locale

    def tr(self, key_path: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Resolves dot-separated key path (e.g. 'device.volume_fix.title').
        Falls back to English if key is missing in active locale.
        Supports formatting variables (e.g., tr('msg.saved', name='AirPods')).
        """
        keys = key_path.split(".")
        
        # 1. Try active translations
        val = self._resolve_keys(self.translations, keys)
        
        # 2. Fall back to English translations
        if val is None:
            val = self._resolve_keys(self.fallback_translations, keys)

        # 3. Fall back to supplied default or key itself
        if val is None:
            val = default if default is not None else key_path

        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except Exception:
                return val

        return str(val)

    @staticmethod
    def _resolve_keys(d: Dict[str, Any], keys: list) -> Optional[str]:
        curr = d
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr if isinstance(curr, str) else None


# Global shortcut for tr()
def tr(key_path: str, default: Optional[str] = None, **kwargs) -> str:
    return Translator.get_instance().tr(key_path, default, **kwargs)
