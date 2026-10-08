"""Short, interruptible transitions for controls; never composite the mpv surface."""

from PySide6.QtCore import QEasingCurve, QEvent, QVariantAnimation, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton


class MotionButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._emphasis = 0.0
        self._hovered = False
        self._motion = QVariantAnimation(self)
        self._motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._motion.valueChanged.connect(self._paint_emphasis)
        self.toggled.connect(self._animate_emphasis)

    def _selected(self):
        return self.isChecked() or bool(self.property("selected")) or bool(self.property("active"))

    def _paint_emphasis(self, value):
        self._emphasis = float(value)
        self.update()

    def _animate_emphasis(self, *_):
        target = 1.0 if self._selected() else (.45 if self._hovered else 0.0)
        self._motion.stop()
        self._motion.setDuration(150)
        self._motion.setStartValue(self._emphasis)
        self._motion.setEndValue(target)
        self._motion.start()

    def enterEvent(self, event):
        self._hovered = True
        self._animate_emphasis()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._animate_emphasis()
        super().leaveEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.DynamicPropertyChange and hasattr(self, "_motion"):
            if bytes(event.propertyName()) in {b"selected", b"active"}:
                self._animate_emphasis()
        return super().event(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._emphasis < .01 or not self.isEnabled():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tint = QColor(self.palette().highlight().color())
        tint.setAlpha(round(24 * self._emphasis))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(tint)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 7, 7)
        if self._selected() and self.objectName() == "sidebarButton":
            tint.setAlpha(round(210 * self._emphasis))
            painter.setBrush(tint)
            x = self.width() - 5 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else 2
            painter.drawRoundedRect(x, self.height() // 2 - 9, 3, 18, 1.5, 1.5)
