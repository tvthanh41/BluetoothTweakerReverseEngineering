from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QComboBox, QSlider, QPushButton, QFrame, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from i18n import tr
from core import BluetoothDevice, RegistryManager, ServiceMonitor, is_admin


class DevicePanel(QScrollArea):
    """
    Right detail panel replicating the clean, exact layout of the original Bluetooth Tweaker UI.
    Only shows relevant sections based on device type (Audio vs Phone vs Peripheral vs Common).
    """
    settings_changed = pyqtSignal(str)  # Emits MAC address

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailScrollArea")
        self.setWidgetResizable(True)
        self.current_device: Optional[BluetoothDevice] = None

        self.container = QWidget()
        self.container.setObjectName("DetailContainer")
        self.setWidget(self.container)

        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(28, 20, 28, 24)
        self.main_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Device Information Section
        # -------------------------------------------------------------
        self.wgt_dev_info = QWidget()
        layout_info = QVBoxLayout(self.wgt_dev_info)
        layout_info.setContentsMargins(0, 0, 0, 0)
        layout_info.setSpacing(6)

        self.lbl_sec_dev_info = QLabel(tr("device_info.title"))
        self.lbl_sec_dev_info.setProperty("class", "SectionTitle")
        layout_info.addWidget(self.lbl_sec_dev_info)

        grid_info = QGridLayout()
        grid_info.setHorizontalSpacing(24)
        grid_info.setVerticalSpacing(6)

        self.lbl_key_name = QLabel(tr("device_info.name"))
        self.lbl_key_name.setProperty("class", "FieldKey")
        self.lbl_val_name = QLabel("—")
        self.lbl_val_name.setProperty("class", "FieldValue")

        self.lbl_key_addr = QLabel(tr("device_info.address"))
        self.lbl_key_addr.setProperty("class", "FieldKey")
        self.lbl_val_addr = QLabel("—")
        self.lbl_val_addr.setProperty("class", "FieldValue")
        self.lbl_val_addr.setStyleSheet("font-family: Consolas, monospace;")

        self.lbl_key_type = QLabel(tr("device_info.type"))
        self.lbl_key_type.setProperty("class", "FieldKey")
        self.lbl_val_type = QLabel("—")
        self.lbl_val_type.setProperty("class", "FieldValue")

        self.lbl_key_status = QLabel(tr("device_info.status"))
        self.lbl_key_status.setProperty("class", "FieldKey")
        self.lbl_val_status = QLabel("—")
        self.lbl_val_status.setProperty("class", "FieldValue")

        grid_info.addWidget(self.lbl_key_name, 0, 0)
        grid_info.addWidget(self.lbl_val_name, 0, 1)
        grid_info.addWidget(self.lbl_key_addr, 1, 0)
        grid_info.addWidget(self.lbl_val_addr, 1, 1)
        grid_info.addWidget(self.lbl_key_type, 2, 0)
        grid_info.addWidget(self.lbl_val_type, 2, 1)
        grid_info.addWidget(self.lbl_key_status, 3, 0)
        grid_info.addWidget(self.lbl_val_status, 3, 1)

        layout_info.addLayout(grid_info)
        self.main_layout.addWidget(self.wgt_dev_info)

        # -------------------------------------------------------------
        # 2. Stereo Audio Volume Control Section (Audio Devices)
        # -------------------------------------------------------------
        self.wgt_volume = QWidget()
        layout_vol = QVBoxLayout(self.wgt_volume)
        layout_vol.setContentsMargins(0, 0, 0, 0)
        layout_vol.setSpacing(6)

        self.lbl_sec_vol = QLabel(tr("volume_control.title"))
        self.lbl_sec_vol.setProperty("class", "SectionTitle")
        layout_vol.addWidget(self.lbl_sec_vol)

        self.lbl_vol_bullet1 = QLabel(tr("volume_control.claim_support"))
        self.lbl_vol_bullet1.setProperty("class", "BulletText")
        self.lbl_vol_bullet2 = QLabel(tr("volume_control.using_hw"))
        self.lbl_vol_bullet2.setProperty("class", "BulletText")
        layout_vol.addWidget(self.lbl_vol_bullet1)
        layout_vol.addWidget(self.lbl_vol_bullet2)

        self.chk_force_software_vol = QCheckBox(tr("volume_control.checkbox"))
        self.chk_force_software_vol.toggled.connect(self._on_vol_override_toggled)
        layout_vol.addWidget(self.chk_force_software_vol)

        self.main_layout.addWidget(self.wgt_volume)

        # -------------------------------------------------------------
        # 3. Headset Microphone Mute Control Section (Audio Devices)
        # -------------------------------------------------------------
        self.wgt_mic = QWidget()
        layout_mic = QVBoxLayout(self.wgt_mic)
        layout_mic.setContentsMargins(0, 0, 0, 0)
        layout_mic.setSpacing(8)

        self.lbl_sec_mic = QLabel(tr("mic_mute.title"))
        self.lbl_sec_mic.setProperty("class", "SectionTitle")
        layout_mic.addWidget(self.lbl_sec_mic)

        mic_row = QHBoxLayout()
        self.lbl_mic_dropdown = QLabel(tr("mic_mute.dropdown_label"))
        self.lbl_mic_dropdown.setStyleSheet("color: #c9d1d9; font-size: 13px;")
        self.cb_mic_mute = QComboBox()
        self.cb_mic_mute.addItem(tr("mic_mute.never"), 0)
        self.cb_mic_mute.addItem(tr("mic_mute.when_in_call"), 1)
        self.cb_mic_mute.addItem(tr("mic_mute.always"), 2)
        self.cb_mic_mute.currentIndexChanged.connect(self._on_mic_mute_changed)

        mic_row.addWidget(self.lbl_mic_dropdown)
        mic_row.addWidget(self.cb_mic_mute)
        mic_row.addStretch()
        layout_mic.addLayout(mic_row)

        slider_row = QHBoxLayout()
        self.lbl_audible_vol = QLabel(tr("mic_mute.audible_volume"))
        self.lbl_audible_vol.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.slider_audible = QSlider(Qt.Horizontal)
        self.slider_audible.setRange(0, 100)
        self.slider_audible.setValue(50)
        self.slider_audible.setFixedWidth(200)

        slider_row.addWidget(self.lbl_audible_vol)
        slider_row.addWidget(self.slider_audible)
        slider_row.addStretch()
        layout_mic.addLayout(slider_row)

        self.main_layout.addWidget(self.wgt_mic)

        # -------------------------------------------------------------
        # 4. Stereo Audio (A2DP) CODEC Information Section (Audio Devices)
        # -------------------------------------------------------------
        self.wgt_codec = QWidget()
        layout_codec = QVBoxLayout(self.wgt_codec)
        layout_codec.setContentsMargins(0, 0, 0, 0)
        layout_codec.setSpacing(6)

        self.lbl_sec_codec = QLabel(tr("codec.title"))
        self.lbl_sec_codec.setProperty("class", "SectionTitle")
        layout_codec.addWidget(self.lbl_sec_codec)

        grid_codec = QGridLayout()
        grid_codec.setHorizontalSpacing(24)
        grid_codec.setVerticalSpacing(8)

        self.lbl_key_supported = QLabel(tr("codec.supported_by_device"))
        self.lbl_key_supported.setProperty("class", "FieldKey")
        self.lbl_val_supported = QLabel("—")
        self.lbl_val_supported.setProperty("class", "FieldValue")
        self.lbl_val_supported.setWordWrap(True)
        self.lbl_val_supported.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.lbl_key_selected = QLabel(tr("codec.selected_by_windows"))
        self.lbl_key_selected.setProperty("class", "FieldKey")
        self.lbl_val_selected = QLabel("—")
        self.lbl_val_selected.setProperty("class", "FieldValue")
        self.lbl_val_selected.setWordWrap(True)
        self.lbl_val_selected.setTextInteractionFlags(Qt.TextSelectableByMouse)

        grid_codec.addWidget(self.lbl_key_supported, 0, 0, Qt.AlignTop)
        grid_codec.addWidget(self.lbl_val_supported, 0, 1)
        grid_codec.addWidget(self.lbl_key_selected, 1, 0, Qt.AlignTop)
        grid_codec.addWidget(self.lbl_val_selected, 1, 1)

        layout_codec.addLayout(grid_codec)

        btn_row = QHBoxLayout()
        self.btn_refresh_codec = QPushButton(tr("codec.btn_refresh"))
        self.btn_refresh_codec.setObjectName("RefreshCodecBtn")
        self.btn_refresh_codec.clicked.connect(self._refresh_codec_info)

        self.btn_copy_codec = QPushButton(tr("codec.btn_copy"))
        self.btn_copy_codec.setObjectName("CopyCodecBtn")
        self.btn_copy_codec.clicked.connect(self._copy_codec_info)

        btn_row.addWidget(self.btn_refresh_codec)
        btn_row.addWidget(self.btn_copy_codec)
        btn_row.addStretch()
        layout_codec.addLayout(btn_row)

        self.main_layout.addWidget(self.wgt_codec)

        # -------------------------------------------------------------
        # 5. A2DP Sink Section (Phone / Audio Source Devices)
        # -------------------------------------------------------------
        self.wgt_a2dp_sink = QWidget()
        layout_sink = QVBoxLayout(self.wgt_a2dp_sink)
        layout_sink.setContentsMargins(0, 0, 0, 0)
        layout_sink.setSpacing(6)

        self.lbl_sec_sink = QLabel(tr("a2dp_sink.title"))
        self.lbl_sec_sink.setProperty("class", "SectionTitle")
        layout_sink.addWidget(self.lbl_sec_sink)

        self.lbl_sink_desc = QLabel(tr("a2dp_sink.desc"))
        self.lbl_sink_desc.setProperty("class", "BulletText")
        self.lbl_sink_desc.setWordWrap(True)
        layout_sink.addWidget(self.lbl_sink_desc)

        self.chk_a2dp_sink = QCheckBox(tr("a2dp_sink.checkbox"))
        self.chk_a2dp_sink.toggled.connect(self._on_a2dp_sink_toggled)
        layout_sink.addWidget(self.chk_a2dp_sink)

        self.main_layout.addWidget(self.wgt_a2dp_sink)

        # -------------------------------------------------------------
        # 6. Peripheral Notice Banner (Non-Audio Devices: Mouse, KB, Gamepad)
        # -------------------------------------------------------------
        self.wgt_peripheral_notice = QFrame()
        self.wgt_peripheral_notice.setObjectName("NoticeBanner")
        layout_notice = QVBoxLayout(self.wgt_peripheral_notice)
        layout_notice.setSpacing(4)

        self.lbl_notice_title = QLabel(tr("peripheral.no_tweak"))
        self.lbl_notice_title.setObjectName("NoticeTitle")
        self.lbl_notice_desc = QLabel("")
        self.lbl_notice_desc.setObjectName("NoticeDesc")
        self.lbl_notice_desc.setWordWrap(True)

        layout_notice.addWidget(self.lbl_notice_title)
        layout_notice.addWidget(self.lbl_notice_desc)
        self.main_layout.addWidget(self.wgt_peripheral_notice)

        # -------------------------------------------------------------
        # 7. Common Settings Section ([Common settings for all devices])
        # -------------------------------------------------------------
        self.wgt_common_settings = QWidget()
        layout_common = QVBoxLayout(self.wgt_common_settings)
        layout_common.setContentsMargins(0, 0, 0, 0)
        layout_common.setSpacing(10)

        self.lbl_sec_common_title = QLabel(tr("common.title"))
        self.lbl_sec_common_title.setProperty("class", "SectionTitle")
        layout_common.addWidget(self.lbl_sec_common_title)

        # AVRCP Proxy Sub-section
        self.lbl_sec_avrcp = QLabel(tr("common.avrcp_title"))
        self.lbl_sec_avrcp.setProperty("class", "SectionTitle")
        layout_common.addWidget(self.lbl_sec_avrcp)

        self.lbl_avrcp_desc = QLabel(tr("common.avrcp_desc"))
        self.lbl_avrcp_desc.setProperty("class", "BulletText")
        self.lbl_avrcp_desc.setWordWrap(True)
        layout_common.addWidget(self.lbl_avrcp_desc)

        self.chk_common_avrcp = QCheckBox(tr("common.avrcp_checkbox"))
        self.chk_common_avrcp.toggled.connect(self._on_common_avrcp_toggled)
        layout_common.addWidget(self.chk_common_avrcp)

        # Service / Driver Status Sub-section
        self.lbl_sec_service = QLabel(tr("common.service_title"))
        self.lbl_sec_service.setProperty("class", "SectionTitle")
        layout_common.addWidget(self.lbl_sec_service)

        self.lbl_common_svc_status = QLabel("Service: Checking...")
        self.lbl_common_svc_status.setProperty("class", "BulletText")
        layout_common.addWidget(self.lbl_common_svc_status)

        self.btn_restart_service = QPushButton(tr("common.btn_restart_service"))
        self.btn_restart_service.clicked.connect(self._restart_service)
        layout_common.addWidget(self.btn_restart_service, 0, Qt.AlignLeft)

        self.main_layout.addWidget(self.wgt_common_settings)

        self.main_layout.addStretch()

    def set_device(self, device: Optional[BluetoothDevice]):
        self.current_device = device

        if device is None:
            # Show Common Settings view
            self._show_view_mode("common")
            self._populate_common_settings()
            return

        device.refresh_params()

        # Update Device Info block
        self.lbl_val_name.setText(device.name)
        self.lbl_val_addr.setText(device.mac_colon_lower)
        self.lbl_val_type.setText(device.transport_type)

        if device.is_connected:
            self.lbl_val_status.setText(f"<span style='color: #3fb950; font-weight: bold;'>● {tr('device_info.connected')}</span>")
        else:
            self.lbl_val_status.setText(f"<span style='color: #8b949e;'>○ {tr('device_info.disconnected')}</span>")

        # Route view mode based on device category
        if device.category == "audio":
            self._show_view_mode("audio")
            self._populate_audio_settings(device)
        elif device.category == "phone":
            self._show_view_mode("phone")
            self._populate_phone_settings(device)
        else:  # peripheral (Keyboard, Mouse, Gamepad)
            self._show_view_mode("peripheral")
            self.lbl_notice_desc.setText(
                tr("peripheral.desc", type=device.name)
            )

    def _show_view_mode(self, mode: str):
        """
        Switches visible widgets dynamically:
        'common'     -> Shows Common Settings only
        'audio'      -> Shows Info, Volume, Mic Mute, Codec
        'phone'      -> Shows Info, A2DP Sink
        'peripheral' -> Shows Info, Peripheral Notice only
        """
        self.wgt_dev_info.setVisible(mode != "common")
        self.wgt_volume.setVisible(mode == "audio")
        self.wgt_mic.setVisible(mode == "audio")
        self.wgt_codec.setVisible(mode == "audio")
        self.wgt_a2dp_sink.setVisible(mode == "phone")
        self.wgt_peripheral_notice.setVisible(mode == "peripheral")
        self.wgt_common_settings.setVisible(mode == "common")

    def _populate_audio_settings(self, device: BluetoothDevice):
        # 1. Volume Override
        is_disabled = device.params.get("disable_hardware_volume", False)
        self.chk_force_software_vol.blockSignals(True)
        self.chk_force_software_vol.setChecked(is_disabled)
        self.chk_force_software_vol.blockSignals(False)

        if is_disabled:
            self.lbl_vol_bullet2.setText(tr("volume_control.using_sw"))
        else:
            self.lbl_vol_bullet2.setText(tr("volume_control.using_hw"))

        # 2. Mic Mute
        mic_val = device.params.get("mic_mute", 0)
        self.cb_mic_mute.blockSignals(True)
        self.cb_mic_mute.setCurrentIndex(1 if mic_val else 0)
        self.cb_mic_mute.blockSignals(False)

        # 3. Codec Information: Show actual info ONLY if connected!
        self._update_codec_display(device)

    def _update_codec_display(self, device: BluetoothDevice, force_refresh: bool = False):
        if not device.is_connected:
            prompt_text = f"<span style='color: #8b949e; font-style: italic; font-size: 13px;'>{tr('codec.please_connect')}</span>"
            self.lbl_val_supported.setText(prompt_text)
            self.lbl_val_selected.setText(prompt_text)
            self.btn_copy_codec.setEnabled(False)
            return

        codecs = device.get_actual_codecs(force_refresh=force_refresh)
        supported_items = codecs.get("supported", [])
        selected_item = codecs.get("selected", "")

        if not supported_items:
            prompt_text = f"<span style='color: #8b949e; font-style: italic; font-size: 13px;'>{tr('codec.please_connect')}</span>"
            self.lbl_val_supported.setText(prompt_text)
            self.lbl_val_selected.setText(prompt_text)
            self.btn_copy_codec.setEnabled(False)
            return

        self.btn_copy_codec.setEnabled(True)

        # Format supported list matching user's image
        sup_html_items = []
        for c in supported_items:
            sup_html_items.append(
                f"<div style='font-family: Consolas, \"Segoe UI\", monospace; font-size: 12.5px; color: #e6edf3; line-height: 1.45;'>{c}</div>"
            )
        self.lbl_val_supported.setText("<div style='height: 8px;'></div>".join(sup_html_items))

        # Format selected codec matching user's image
        html_sel = f"<div style='font-family: Consolas, \"Segoe UI\", monospace; font-size: 12.5px; color: #e6edf3; line-height: 1.45;'>{selected_item}</div>"
        self.lbl_val_selected.setText(html_sel)

    def _refresh_codec_info(self):
        if not self.current_device:
            return

        from core.device_manager import get_connected_bluetooth_macs
        from PyQt5.QtCore import QTimer

        # 1. Update live connection status from Windows Bluetooth stack
        connected = get_connected_bluetooth_macs()
        self.current_device.is_connected = (self.current_device.mac in connected)
        self.lbl_val_status.setText(tr("device_info.status_connected") if self.current_device.is_connected else tr("device_info.status_disconnected"))
        self.lbl_val_status.setStyleSheet(f"color: {'#3fb950' if self.current_device.is_connected else '#8b949e'}; font-weight: 600;")
        self.current_device.refresh_params()

        # 2. Live re-probe kernel driver trace logs & Windows audio engine (force_refresh=True)
        self._update_codec_display(self.current_device, force_refresh=True)

        # 3. Smooth, non-blocking visual feedback directly on the button
        self.btn_refresh_codec.setText(tr("codec.btn_refreshed"))
        self.btn_refresh_codec.setEnabled(False)
        QTimer.singleShot(1500, lambda: (
            self.btn_refresh_codec.setText(tr("codec.btn_refresh")),
            self.btn_refresh_codec.setEnabled(True)
        ))

    def _copy_codec_info(self):
        if not self.current_device:
            return
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        codecs = self.current_device.get_actual_codecs()
        text = f"Device: {self.current_device.name} ({self.current_device.mac_colon_lower})\n\n"
        text += "CODEC supported by device:\n"
        for s in codecs["supported"]:
            text += f"{s}\n"
        text += f"\nCODEC selected by Windows:\n{codecs['selected']}\n"
        QApplication.clipboard().setText(text)
        self.btn_copy_codec.setText(tr("codec.btn_copied"))
        QTimer.singleShot(2000, lambda: self.btn_copy_codec.setText(tr("codec.btn_copy")))

    def _populate_phone_settings(self, device: BluetoothDevice):
        is_sink = device.params.get("a2dp_sink", False)
        self.chk_a2dp_sink.blockSignals(True)
        self.chk_a2dp_sink.setChecked(is_sink)
        self.chk_a2dp_sink.blockSignals(False)

    def _populate_common_settings(self):
        # Read service & driver status
        status = ServiceMonitor.get_status()
        s_text = f"• BtTweakerSvc Service: <b style='color: {'#3fb950' if status['service_running'] else '#f85149'}'>{status['service_status']}</b><br>"
        s_text += f"• BtTweakerFltr Filter Driver: <b style='color: #3fb950'>{status['driver_status']}</b>"
        self.lbl_common_svc_status.setText(s_text)

    def _on_vol_override_toggled(self, checked: bool):
        if not self.current_device:
            return

        if not is_admin():
            self.chk_force_software_vol.blockSignals(True)
            self.chk_force_software_vol.setChecked(not checked)
            self.chk_force_software_vol.blockSignals(False)
            QMessageBox.warning(self, tr("app.title"), tr("messages.admin_needed"))
            return

        success = RegistryManager.set_hardware_volume_override(self.current_device.mac, checked)
        if success:
            self.current_device.refresh_params()
            if checked:
                self.lbl_vol_bullet2.setText(tr("volume_control.using_sw"))
            else:
                self.lbl_vol_bullet2.setText(tr("volume_control.using_hw"))
            self.settings_changed.emit(self.current_device.mac)
        else:
            QMessageBox.critical(self, tr("app.title"), tr("messages.save_error", error="Registry Write Failed"))

    def _on_mic_mute_changed(self, index: int):
        if not self.current_device:
            return

        if not is_admin():
            QMessageBox.warning(self, tr("app.title"), tr("messages.admin_needed"))
            return

        muted = (index > 0)
        success = RegistryManager.set_mic_mute(self.current_device.mac, muted)
        if success:
            self.current_device.refresh_params()
            self.settings_changed.emit(self.current_device.mac)

    def _on_a2dp_sink_toggled(self, checked: bool):
        if not self.current_device:
            return

        if not is_admin():
            self.chk_a2dp_sink.blockSignals(True)
            self.chk_a2dp_sink.setChecked(not checked)
            self.chk_a2dp_sink.blockSignals(False)
            QMessageBox.warning(self, tr("app.title"), tr("messages.admin_needed"))
            return

        success = RegistryManager.set_a2dp_sink(self.current_device.mac, checked)
        if success:
            self.current_device.refresh_params()
            self.settings_changed.emit(self.current_device.mac)

    def _on_common_avrcp_toggled(self, checked: bool):
        if not is_admin():
            QMessageBox.warning(self, tr("app.title"), tr("messages.admin_needed"))
            return
        # Set global AVRCP proxy for configured devices
        for dev in RegistryManager.get_configured_devices():
            RegistryManager.set_avrcp_proxy(dev, checked)

    def _restart_service(self):
        if not is_admin():
            QMessageBox.warning(self, tr("app.title"), tr("messages.admin_needed"))
            return
        ServiceMonitor.restart_service()
        self._populate_common_settings()

    def retranslate_ui(self):
        self.lbl_sec_dev_info.setText(tr("device_info.title"))
        self.lbl_key_name.setText(tr("device_info.name"))
        self.lbl_key_addr.setText(tr("device_info.address"))
        self.lbl_key_type.setText(tr("device_info.type"))
        self.lbl_key_status.setText(tr("device_info.status"))

        self.lbl_sec_vol.setText(tr("volume_control.title"))
        self.lbl_vol_bullet1.setText(tr("volume_control.claim_support"))
        self.chk_force_software_vol.setText(tr("volume_control.checkbox"))

        self.lbl_sec_mic.setText(tr("mic_mute.title"))
        self.lbl_mic_dropdown.setText(tr("mic_mute.dropdown_label"))
        self.lbl_audible_vol.setText(tr("mic_mute.audible_volume"))

        self.lbl_sec_codec.setText(tr("codec.title"))
        self.lbl_key_supported.setText(tr("codec.supported_by_device"))
        self.lbl_key_selected.setText(tr("codec.selected_by_windows"))
        self.btn_refresh_codec.setText(tr("codec.btn_refresh"))
        self.btn_copy_codec.setText(tr("codec.btn_copy"))

        self.lbl_sec_sink.setText(tr("a2dp_sink.title"))
        self.lbl_sink_desc.setText(tr("a2dp_sink.desc"))
        self.chk_a2dp_sink.setText(tr("a2dp_sink.checkbox"))

        self.lbl_notice_title.setText(tr("peripheral.no_tweak"))
        self.lbl_sec_common_title.setText(tr("common.title"))
        self.lbl_sec_avrcp.setText(tr("common.avrcp_title"))
        self.lbl_avrcp_desc.setText(tr("common.avrcp_desc"))
        self.chk_common_avrcp.setText(tr("common.avrcp_checkbox"))
        self.lbl_sec_service.setText(tr("common.service_title"))
        self.btn_restart_service.setText(tr("common.btn_restart_service"))

        self.set_device(self.current_device)
