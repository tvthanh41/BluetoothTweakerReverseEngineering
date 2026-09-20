from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QStatusBar
)
from PyQt5.QtCore import Qt
from i18n import Translator, tr
from .styles import DARK_THEME_QSS
from .widgets import ServiceBar, DeviceSidebar, DevicePanel


class MainWindow(QMainWindow):
    """
    Main application window replicating the original clean Bluetooth Tweaker structure.
    """

    def __init__(self):
        super().__init__()
        self.translator = Translator.get_instance()
        self._init_window()
        self._init_layout()
        self._connect_signals()

        # Load devices and select initial device
        self.sidebar.reload_devices()

    def _init_window(self):
        self.setWindowTitle(tr("app.title"))
        self.resize(980, 680)
        self.setMinimumSize(800, 560)
        self.setStyleSheet(DARK_THEME_QSS)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #12151c; color: #8b949e; border-top: 1px solid #21262d; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"{tr('app.title')} {tr('app.version')} — {tr('app.unlicensed_badge')}")

    def _init_layout(self):
        central_widget = QWidget()
        central_widget.setObjectName("MainContainer")
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 1. Top Ribbon
        self.service_bar = ServiceBar(self)
        main_vbox.addWidget(self.service_bar, 0)

        # 2. Main Horizontal Splitter (Sidebar + Detail Panel)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #21262d; }")

        self.sidebar = DeviceSidebar(self)
        self.panel = DevicePanel(self)

        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_vbox.addWidget(self.splitter, 1)

    def _connect_signals(self):
        # Sidebar selection changed -> update detail panel
        self.sidebar.device_selected.connect(self.panel.set_device)

        # Settings changed in panel -> update status
        self.panel.settings_changed.connect(self._on_settings_changed)

        # Refresh button in top ribbon
        self.service_bar.refresh_requested.connect(self._on_refresh_requested)

        # Language changed
        self.translator.language_changed.connect(self._retranslate_ui)

    def _on_settings_changed(self, mac: str):
        self.status_bar.showMessage(tr("messages.saved", mac=mac), 4000)

    def _on_refresh_requested(self):
        curr_dev = self.sidebar.get_selected_device()
        curr_mac = curr_dev.mac if curr_dev else None
        self.sidebar.reload_devices(keep_selection_mac=curr_mac)
        self.service_bar.update_admin_status()
        self.status_bar.showMessage("Devices and status refreshed.", 3000)

    def _retranslate_ui(self, locale_code: str):
        self.setWindowTitle(tr("app.title"))
        self.service_bar.retranslate_ui()
        self.sidebar.retranslate_ui()
        self.panel.retranslate_ui()
        self.status_bar.showMessage(f"{tr('app.title')} — {tr('app.unlicensed_badge')}")
