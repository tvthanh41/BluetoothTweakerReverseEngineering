"""
Modern Dark Theme QSS Stylesheet replicating the original clean Bluetooth Tweaker structure.
"""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget#MainContainer {
    background-color: #0f1117;
    color: #e6edf3;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #c9d1d9;
    font-size: 13px;
    selection-background-color: #0969da;
    selection-color: #ffffff;
}

/* Header Ribbon (Ultra-compact 36px) */
QFrame#HeaderRibbon {
    background-color: #161b22;
    border-bottom: 1px solid #21262d;
    min-height: 36px;
    max-height: 36px;
    height: 36px;
}

QLabel#AppTitle {
    font-size: 14px;
    font-weight: 700;
    color: #58a6ff;
}

QLabel#AppSubtitle {
    font-size: 11px;
    color: #8b949e;
}

/* Left Sidebar */
QFrame#SidebarFrame {
    background-color: #12151c;
    border-right: 1px solid #21262d;
}

QLabel#SidebarPrompt {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
    padding: 4px 6px 6px 6px;
}

QListWidget#DeviceListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget#DeviceListWidget::item {
    color: #c9d1d9;
    padding: 7px 10px;
    border-radius: 4px;
    margin: 1px 4px;
}

QListWidget#DeviceListWidget::item:hover {
    background-color: #1f242c;
    color: #f0f6fc;
}

QListWidget#DeviceListWidget::item:selected {
    background-color: #0969da;
    color: #ffffff;
    font-weight: 600;
}

/* Right Detail Panel */
QScrollArea#DetailScrollArea {
    background-color: #0f1117;
    border: none;
}

QWidget#DetailContainer {
    background-color: #0f1117;
}

/* Section Header & Subheaders */
QLabel.SectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: #58a6ff;
    margin-top: 14px;
    margin-bottom: 4px;
}

QLabel.SectionLink {
    font-size: 12px;
    color: #58a6ff;
    text-decoration: underline;
    margin-left: 6px;
}

QLabel.SectionLink:hover {
    color: #79c0ff;
}

/* Two-column Key Value Table */
QLabel.FieldKey {
    color: #8b949e;
    font-size: 13px;
    min-width: 190px;
}

QLabel.FieldValue {
    color: #f0f6fc;
    font-size: 13px;
}

QLabel.BulletText {
    color: #c9d1d9;
    font-size: 13px;
    line-height: 1.4;
    margin-left: 4px;
}

/* Device & Codec Dynamic Status / Hint Styles */
QLabel#DeviceAddressValue {
    font-family: Consolas, monospace;
}

QLabel#MicDropdownLabel {
    color: #c9d1d9;
    font-size: 13px;
}

QLabel#AudibleVolLabel {
    color: #8b949e;
    font-size: 12px;
}

QLabel.StatusConnected {
    color: #3fb950;
    font-weight: 600;
}

QLabel.StatusDisconnected {
    color: #8b949e;
    font-weight: 400;
}

QLabel.CodecHintMuted {
    color: #8b949e;
    font-style: italic;
    font-size: 13px;
}

QLabel.CodecHintWarning {
    color: #e3b341;
    font-style: italic;
    font-size: 12px;
}

QLabel.CodecHintDanger {
    color: #f85149;
    font-style: italic;
    font-size: 12px;
}

QLabel.CodecValue {
    font-family: Consolas, "Segoe UI", monospace;
    font-size: 12.5px;
    color: #e6edf3;
    line-height: 1.45;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #f0f6fc;
    font-size: 13px;
    margin-top: 4px;
    margin-bottom: 4px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 3px;
    border: 1px solid #484f58;
    background-color: #161b22;
}

QCheckBox::indicator:hover {
    border-color: #58a6ff;
}

QCheckBox::indicator:checked {
    background-color: #0969da;
    border-color: #0969da;
    image: none;
}

/* Dropdowns */
QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 2px 8px;
    color: #c9d1d9;
    font-size: 12px;
    min-width: 120px;
    height: 24px;
    max-height: 24px;
}

QComboBox:hover {
    border-color: #58a6ff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #0969da;
    selection-color: #ffffff;
    color: #c9d1d9;
    padding: 4px;
}

/* Slider */
QSlider::groove:horizontal {
    height: 4px;
    background: #30363d;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0969da;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #f0f6fc;
    border: 1px solid #0969da;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #58a6ff;
}

/* Buttons */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #c9d1d9;
    padding: 3px 12px;
    font-weight: 600;
    font-size: 12px;
    height: 24px;
    max-height: 24px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton#RefreshCodecBtn, QPushButton#CopyCodecBtn {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 4px 16px;
    margin-top: 6px;
    height: 28px;
    max-height: 28px;
}

QPushButton#RefreshCodecBtn:hover, QPushButton#CopyCodecBtn:hover {
    background-color: #21262d;
    border-color: #58a6ff;
}

QPushButton#CopyCodecBtn:disabled {
    color: #484f58;
    border-color: #21262d;
    background-color: #0d1117;
}

/* Peripheral / Notice Banner */
QFrame#NoticeBanner {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 14px 18px;
    margin-top: 16px;
}

QLabel#NoticeTitle {
    color: #f0f6fc;
    font-weight: 600;
    font-size: 13px;
}

QLabel#NoticeDesc {
    color: #8b949e;
    font-size: 12px;
    margin-top: 4px;
}

/* Status Badges in Header */
QLabel.PillBadge {
    padding: 2px 8px;
    border-radius: 11px;
    font-size: 11px;
    font-weight: 600;
    height: 22px;
    max-height: 22px;
}

QLabel#BadgeAdmin {
    background-color: rgba(137, 87, 229, 0.2);
    color: #d2a8ff;
    border: 1px solid rgba(163, 113, 247, 0.4);
}

QLabel#BadgeNonAdmin {
    background-color: rgba(210, 153, 34, 0.2);
    color: #e3b341;
    border: 1px solid rgba(210, 153, 34, 0.4);
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
