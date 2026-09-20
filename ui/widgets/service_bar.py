import sys
import os
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from i18n import Translator, tr
from core import is_admin


class ServiceBar(QFrame):
    """
    Ultra-compact, sleek top header bar (34px height).
    """
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderRibbon")
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.translator = Translator.get_instance()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        # Title
        self.lbl_title = QLabel(tr("app.title"))
        self.lbl_title.setObjectName("AppTitle")
        self.lbl_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(self.lbl_title, 0, Qt.AlignVCenter)

        layout.addStretch(1)

        # Admin Badge / Elevate button
        self.badge_admin = QLabel("")
        self.badge_admin.setProperty("class", "PillBadge")
        self.badge_admin.setFixedHeight(22)
        self.badge_admin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(self.badge_admin, 0, Qt.AlignVCenter)

        self.btn_elevate = QPushButton(tr("app.elevate_button"))
        self.btn_elevate.setFixedHeight(24)
        self.btn_elevate.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_elevate.clicked.connect(self._elevate_process)
        layout.addWidget(self.btn_elevate, 0, Qt.AlignVCenter)

        # Language dropdown
        self.cb_lang = QComboBox()
        self.cb_lang.setFixedHeight(24)
        self.cb_lang.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for code, name in self.translator.SUPPORTED_LANGUAGES.items():
            self.cb_lang.addItem(name, code)
        
        idx = self.cb_lang.findData(self.translator.get_locale())
        if idx >= 0:
            self.cb_lang.setCurrentIndex(idx)
        self.cb_lang.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self.cb_lang, 0, Qt.AlignVCenter)

        # Refresh button
        self.btn_refresh = QPushButton(f"🔄 {tr('service_bar.btn_refresh')}")
        self.btn_refresh.setFixedHeight(24)
        self.btn_refresh.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.btn_refresh, 0, Qt.AlignVCenter)

        self.update_admin_status()

    def _on_language_changed(self, index: int):
        code = self.cb_lang.itemData(index)
        if code:
            self.translator.set_locale(code)

    def _elevate_process(self):
        import ctypes
        python_exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = f'"{script}"'
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, params, None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"[-] UAC Elevation failed: {e}")

    def update_admin_status(self):
        admin = is_admin()
        if admin:
            self.badge_admin.setText(f"✓ {tr('app.admin_badge')}")
            self.badge_admin.setObjectName("BadgeAdmin")
            self.btn_elevate.setVisible(False)
        else:
            self.badge_admin.setText(f"⚠️ {tr('app.non_admin_badge')}")
            self.badge_admin.setObjectName("BadgeNonAdmin")
            self.btn_elevate.setVisible(True)

        self.badge_admin.style().unpolish(self.badge_admin)
        self.badge_admin.style().polish(self.badge_admin)

    def retranslate_ui(self):
        self.lbl_title.setText(tr("app.title"))
        self.btn_elevate.setText(tr("app.elevate_button"))
        self.btn_refresh.setText(f"🔄 {tr('service_bar.btn_refresh')}")
        self.update_admin_status()
