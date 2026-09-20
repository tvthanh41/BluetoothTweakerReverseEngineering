from typing import List, Optional
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from i18n import tr
from core import BluetoothDevice, DeviceManager


class DeviceSidebar(QFrame):
    """
    Left sidebar matching the original Bluetooth Tweaker device selection pane.
    Contains:
    - Label: "Please select a device to tweak:"
    - Item 0: "[Common settings for all devices]"
    - Items 1..N: Alphabetical list of paired devices.
    """
    device_selected = pyqtSignal(object)  # Emits BluetoothDevice or None (for common settings)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(260)
        self.devices: List[BluetoothDevice] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        # Header Label
        self.lbl_prompt = QLabel(tr("sidebar.select_prompt"))
        self.lbl_prompt.setObjectName("SidebarPrompt")
        layout.addWidget(self.lbl_prompt)

        # Device List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("DeviceListWidget")
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

    def reload_devices(self, keep_selection_mac: Optional[str] = None):
        self.devices = DeviceManager.get_paired_devices()
        self._render_list(keep_selection_mac)

    def _render_list(self, target_mac: Optional[str] = None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        # Item 0: [Common settings for all devices]
        common_item = QListWidgetItem(tr("sidebar.common_settings"))
        common_item.setData(Qt.UserRole, None)  # None represents common settings
        self.list_widget.addItem(common_item)

        matched_item = None

        # Items 1..N: Paired devices
        for dev in self.devices:
            status_dot = " ●" if dev.is_connected else ""
            item_text = f"{dev.name}{status_dot}"
            item = QListWidgetItem(item_text)
            if dev.is_connected:
                item.setForeground(Qt.white)
            item.setData(Qt.UserRole, dev)
            self.list_widget.addItem(item)

            if target_mac and dev.mac == target_mac.lower():
                matched_item = item

        self.list_widget.blockSignals(False)

        # Restore or set default selection
        if matched_item:
            self.list_widget.setCurrentItem(matched_item)
        elif self.list_widget.count() > 1:
            # Select first real device by default (e.g. index 1) or target
            self.list_widget.setCurrentRow(1)
        else:
            self.list_widget.setCurrentRow(0)

    def _on_item_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            dev = current.data(Qt.UserRole)
            self.device_selected.emit(dev)

    def get_selected_device(self) -> Optional[BluetoothDevice]:
        curr = self.list_widget.currentItem()
        if curr:
            return curr.data(Qt.UserRole)
        return None

    def retranslate_ui(self):
        self.lbl_prompt.setText(tr("sidebar.select_prompt"))
        curr_dev = self.get_selected_device()
        curr_mac = curr_dev.mac if curr_dev else None
        self._render_list(curr_mac)
