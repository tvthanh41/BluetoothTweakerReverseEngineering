from typing import Optional, List, Dict, Any
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGridLayout, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from i18n import tr
from core import BluetoothDevice, CodecDecoder


class CodecView(QFrame):
    """
    Card inspecting and selecting Bluetooth Stereo (A2DP) CODECs.
    Decodes real AVDTP capability payloads and formats technical parameters.
    """
    codec_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "FeatureCard")
        self.current_device: Optional[BluetoothDevice] = None
        self.codecs_list: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: Title + Badge + Copy Button
        hdr = QHBoxLayout()
        self.lbl_title = QLabel(tr("codec.title"))
        self.lbl_title.setProperty("class", "CardTitle")
        
        self.badge = QLabel(tr("codec.badge"))
        self.badge.setProperty("class", "CardBadge")

        self.btn_copy = QPushButton(f"📋 {tr('codec.btn_copy_info')}")
        self.btn_copy.clicked.connect(self._copy_codec_info)

        hdr.addWidget(self.lbl_title)
        hdr.addWidget(self.badge)
        hdr.addStretch()
        hdr.addWidget(self.btn_copy)
        layout.addLayout(hdr)

        # Description
        self.lbl_desc = QLabel(tr("codec.desc"))
        self.lbl_desc.setProperty("class", "CardDesc")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # Codec Selector / Active Codec Row
        select_row = QHBoxLayout()
        select_row.setSpacing(12)

        self.lbl_active_title = QLabel(tr("codec.current_codec"))
        self.lbl_active_title.setStyleSheet("font-weight: 600; color: #c9d1d9;")
        self.lbl_active_val = QLabel("SBC (Standard)")
        self.lbl_active_val.setStyleSheet("color: #3fb950; font-weight: bold; background-color: rgba(35, 134, 54, 0.2); padding: 3px 8px; border-radius: 4px;")

        self.lbl_desired_title = QLabel(tr("codec.desired_codec"))
        self.lbl_desired_title.setStyleSheet("font-weight: 600; color: #c9d1d9;")

        self.cb_codec = QComboBox()
        self.cb_codec.addItem(tr("codec.codec_default"), 1)
        self.cb_codec.currentIndexChanged.connect(self._on_codec_selected)

        select_row.addWidget(self.lbl_active_title)
        select_row.addWidget(self.lbl_active_val)
        select_row.addSpacing(16)
        select_row.addWidget(self.lbl_desired_title)
        select_row.addWidget(self.cb_codec)
        select_row.addStretch()
        layout.addLayout(select_row)

        # Supported Codecs Container
        self.lbl_supported_title = QLabel(tr("codec.supported_by_device"))
        self.lbl_supported_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #58a6ff; margin-top: 8px;")
        layout.addWidget(self.lbl_supported_title)

        self.specs_container = QVBoxLayout()
        self.specs_container.setSpacing(8)
        layout.addLayout(self.specs_container)

    def set_device(self, device: Optional[BluetoothDevice]):
        self.current_device = device
        if not device:
            self._clear_specs()
            return

        # Determine codecs from raw A2DP data or default audio profile
        raw_data = device.params.get("a2dp_sink_data")
        self.codecs_list = CodecDecoder.get_supported_codecs_list(raw_data)

        # Desired codec combo index
        current_next = device.params.get("codec_next", 1)
        idx = self.cb_codec.findData(current_next)
        if idx >= 0:
            self.cb_codec.setCurrentIndex(idx)

        self._render_specs()

    def _clear_specs(self):
        while self.specs_container.count():
            item = self.specs_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget(): sub.widget().deleteLater()

    def _render_specs(self):
        self._clear_specs()

        if not self.codecs_list:
            lbl_none = QLabel(tr("codec.no_codec_data"))
            lbl_none.setStyleSheet("color: #8b949e; font-style: italic; padding: 8px;")
            self.specs_container.addWidget(lbl_none)
            return

        for c in self.codecs_list:
            card = QFrame()
            card.setStyleSheet("background-color: #12151c; border: 1px solid #262f40; border-radius: 6px; padding: 10px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(6)

            # Codec Name + Category
            top_h = QHBoxLayout()
            c_name = QLabel(f"🎵 {c.get('codec_name', 'Unknown')}")
            c_name.setStyleSheet("font-weight: 700; font-size: 13px; color: #f0f6fc;")
            c_cat = QLabel(c.get('codec_category', 'Audio'))
            c_cat.setStyleSheet("color: #8b949e; font-size: 11px;")
            top_h.addWidget(c_name)
            top_h.addStretch()
            top_h.addWidget(c_cat)
            card_layout.addLayout(top_h)

            # Technical details grid
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(4)

            row = 0
            if c.get("sample_rates"):
                grid.addWidget(QLabel(tr("codec.sample_rates")), row, 0)
                val_sr = QLabel(" / ".join(c["sample_rates"]))
                val_sr.setStyleSheet("color: #79c0ff; font-weight: 600;")
                grid.addWidget(val_sr, row, 1)
                row += 1

            if c.get("channel_modes"):
                grid.addWidget(QLabel(tr("codec.channel_modes")), row, 0)
                val_cm = QLabel(" / ".join(c["channel_modes"]))
                val_cm.setStyleSheet("color: #d2a8ff;")
                grid.addWidget(val_cm, row, 1)
                row += 1

            for k, v in c.get("details", {}).items():
                grid.addWidget(QLabel(f"{k}:"), row, 0)
                val_k = QLabel(str(v))
                val_k.setStyleSheet("color: #e6edf3;")
                grid.addWidget(val_k, row, 1)
                row += 1

            card_layout.addLayout(grid)
            self.specs_container.addWidget(card)

    def _on_codec_selected(self, index: int):
        val = self.cb_codec.itemData(index)
        if val is not None:
            self.codec_changed.emit(val)

    def _copy_codec_info(self):
        if not self.current_device:
            return

        lines = [
            f"Device: {self.current_device.name} ({self.current_device.mac_formatted})",
            f"Active CODEC: {self.lbl_active_val.text()}",
            "Supported CODECs:"
        ]
        for c in self.codecs_list:
            lines.append(f"\n- {c.get('codec_name')} ({c.get('codec_category')})")
            if c.get("sample_rates"):
                lines.append(f"  Sample Rates: {', '.join(c['sample_rates'])}")
            if c.get("channel_modes"):
                lines.append(f"  Channel Modes: {', '.join(c['channel_modes'])}")
            for k, v in c.get("details", {}).items():
                lines.append(f"  {k}: {v}")

        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.btn_copy.setText(f"✓ {tr('messages.copied')}")

    def retranslate_ui(self):
        self.lbl_title.setText(tr("codec.title"))
        self.badge.setText(tr("codec.badge"))
        self.lbl_desc.setText(tr("codec.desc"))
        self.lbl_active_title.setText(tr("codec.current_codec"))
        self.lbl_desired_title.setText(tr("codec.desired_codec"))
        self.lbl_supported_title.setText(tr("codec.supported_by_device"))
        self.btn_copy.setText(f"📋 {tr('codec.btn_copy_info')}")
        self.set_device(self.current_device)
