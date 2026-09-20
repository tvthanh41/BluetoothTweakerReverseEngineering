from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSwitch(QWidget):
    """
    Modern iOS / Fluent animated toggle switch.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.PointingHandCursor)

        self._checked = checked
        self._thumb_position = 23.0 if checked else 3.0

        # Animation for smooth thumb sliding
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)

    @pyqtProperty(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._start_animation()
            self.toggled.emit(self._checked)

    def _start_animation(self):
        self._anim.stop()
        target = 25.0 if self._checked else 3.0
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Track colors
        if self._checked:
            track_bg = QColor("#238636")  # Vibrant Emerald
            border_col = QColor("#2ea043")
        else:
            track_bg = QColor("#21262d")  # Dark Slate
            border_col = QColor("#30363d")

        # Draw pill track
        track_rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(QPen(border_col, 1))
        painter.setBrush(QBrush(track_bg))
        painter.drawRoundedRect(track_rect, 13, 13)

        # Draw circle thumb
        thumb_diameter = 20.0
        thumb_rect = QRectF(self._thumb_position, 3.0, thumb_diameter, thumb_diameter)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(thumb_rect)
        painter.end()
