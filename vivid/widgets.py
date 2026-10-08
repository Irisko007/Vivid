import hashlib
from pathlib import Path
import shutil
import subprocess
import threading
import time

from PySide6.QtCore import QObject, QPoint, QPropertyAnimation, QEasingCurve, QRunnable, QRectF, QSize, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget

from .i18n import bind_text, tr
from .icons import ASSETS, icon
from .motion import MotionButton
from .storage import timestamp


def label(text, name=None):
    w = QLabel(text)
    bind_text(w, "setText", text)
    if name:
        w.setObjectName(name)
    if name == "badge":
        w.setFixedHeight(27)
    return w


def button(text, symbol=None, callback=None, primary=False):
    w = MotionButton(text)
    bind_text(w, "setText", text)
    w.setCursor(Qt.CursorShape.PointingHandCursor)
    if symbol:
        w._icon_symbol = symbol
        w._icon_role = "white" if primary else "muted"
        w.setIcon(icon(symbol, "#ffffff" if primary else "#64748b"))
        w.setIconSize(QSize(18, 18))
    if primary:
        w.setObjectName("primary")
    if callback:
        w.clicked.connect(callback)
    return w


def tool(symbol, tooltip, callback=None, color="#64748b", size=36):
    w = button("", callback=callback)
    w.setIcon(icon(symbol, color))
    w._icon_symbol = symbol
    w._icon_role = "white" if color == "#ffffff" else ("blue" if color == "#2563eb" else "muted")
    w.setIconSize(QSize(20, 20))
    w.setFixedSize(size, size)
    bind_text(w, 'setToolTip', tooltip)
    bind_text(w, 'setAccessibleName', tooltip)
    w.setStyleSheet("padding: 6px;")
    return w


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.full_text = text
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bind_text(self, 'setText', text)

    def setText(self, text):
        self.full_text = text
        super().setText(self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(1, self.width())))

    def resizeEvent(self, event):
        self.setText(self.full_text)
        super().resizeEvent(event)


class FileDialogProxy(QSortFilterProxyModel):
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and section < 4:
            return [tr('Name'), tr('Size'), tr('Type'), tr('Modified')][section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        value = super().data(index, role)
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 2 and value in {"Folder", "Directory"}:
            return tr('Folder')
        return value


class SidebarButton(MotionButton):
    def __init__(self, text, symbol, callback, secondary=None):
        super().__init__()
        self.setObjectName("sidebarButton")
        self.setFixedHeight(44 if secondary is None else 66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_symbol, self._icon_role = symbol, "muted"
        row = QHBoxLayout(self)
        row.setContentsMargins(13, 0, 13, 0)
        row.setSpacing(12)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        row.addWidget(self.icon_label)
        labels = QVBoxLayout()
        labels.setContentsMargins(0, 0, 0, 0)
        labels.setSpacing(3)
        self.text_label = ElidedLabel(text)
        self.text_label.setStyleSheet("font-weight: 500;")
        labels.addWidget(self.text_label)
        if secondary is not None:
            self.secondary_label = label(secondary, "trackStatus")
            labels.addWidget(self.secondary_label)
        row.addLayout(labels, 1)
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setIcon(icon(symbol))
        bind_text(self, 'setText', text)
        self.clicked.connect(callback)

    def setText(self, text):
        super().setText("")
        if hasattr(self, "text_label"):
            bind_text(self.text_label, 'setText', text)
        bind_text(self, 'setAccessibleName', text)

    def setIcon(self, value):
        # Render on a fixed grid so all sidebar captions start at the same x.
        if hasattr(self, "icon_label"):
            self.icon_label.setPixmap(value.pixmap(20, 20))


class SpeedPicker(MotionButton):
    currentIndexChanged = Signal(int)
    rates = [.25, .5, .75, 1, 1.25, 1.5, 1.75, 2]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 1.0
        self.setObjectName("speedButton")
        self.setFixedSize(78, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        bind_text(self, 'setToolTip', tr('Playback speed'))
        bind_text(self, 'setAccessibleName', tr('Playback speed'))
        bind_text(self, 'setText', "1×  ▾")
        self.clicked.connect(self.show_picker)

    def currentData(self):
        return self.value

    def setCurrentIndex(self, index):
        self.setValue(self.rates[index])

    def setValue(self, value, emit=True):
        if value not in self.rates:
            return
        changed = self.value != value
        self.value = value
        bind_text(self, 'setText', f"{value:g}×  ▾")
        self.setProperty("active", value != 1.0)
        self.style().unpolish(self)
        self.style().polish(self)
        if changed and emit:
            self.currentIndexChanged.emit(self.rates.index(value))

    def create_popup(self):
        popup = QDialog(self, Qt.WindowType.Popup)
        popup.setObjectName("speedPopup")
        popup.setFixedWidth(250)
        col = QVBoxLayout(popup)
        col.setContentsMargins(16, 16, 16, 16)
        col.setSpacing(10)
        title = label(tr('Playback speed'))
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        col.addWidget(title)
        col.addWidget(label(tr('Choose your pace'), "muted"))
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, rate in enumerate(self.rates):
            choice = button(f"{rate:g}×", callback=lambda checked=False, r=rate: (self.setValue(r), popup.accept()))
            choice.setObjectName("speedOption")
            choice.setProperty("selected", self.value == rate)
            choice.setFixedHeight(42)
            bind_text(choice, 'setAccessibleName', tr("Speed {rate}", rate=f"{rate:g}"))
            grid.addWidget(choice, i // 2, i % 2)
        col.addLayout(grid)
        return popup

    def show_picker(self):
        self.popup = self.create_popup()
        self.popup.adjustSize()
        screen = self.screen().availableGeometry()
        point = self.mapToGlobal(QPoint(0, -self.popup.height() - 8))
        point.setX(max(screen.left(), min(point.x(), screen.right() - self.popup.width())))
        point.setY(max(screen.top(), min(point.y(), screen.bottom() - self.popup.height())))
        self.popup.move(point)
        self.popup.setWindowOpacity(0.0)
        self.popup.show()
        self.popup.fade = QPropertyAnimation(self.popup, b"windowOpacity", self.popup)
        self.popup.fade.setDuration(140)
        self.popup.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.popup.fade.setStartValue(0.0)
        self.popup.fade.setEndValue(1.0)
        self.popup.fade.start()


class ThemeChoice(MotionButton):
    def __init__(self, name, colors, callback):
        super().__init__()
        name = tr(name)
        self.setObjectName("themeChoice")
        self.setFixedHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        col = QVBoxLayout(self)
        col.setContentsMargins(12, 10, 12, 8)
        col.setSpacing(5)
        strip = QPixmap(144, 22)
        strip.fill(Qt.GlobalColor.transparent)
        painter = QPainter(strip)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, color in enumerate([colors["sidebar"], colors["bg"], colors["panel"], colors["accent"]]):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(i * 36, 0, 32, 22), 4, 4)
        painter.end()
        preview = QLabel()
        preview.setPixmap(strip)
        caption = label(name)
        caption.setStyleSheet("font-size: 12px; font-weight: 500;")
        col.addWidget(preview)
        col.addWidget(caption)
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        bind_text(self, 'setAccessibleName', name)
        self.clicked.connect(callback)


class Hero(QFrame):
    def __init__(self, open_files, parent=None):
        super().__init__(parent)
        self.setFixedHeight(250)
        self.pix = QPixmap(str(ASSETS / "vivid.png"))
        row = QHBoxLayout(self)
        row.setContentsMargins(30, 24, 28, 24)
        col = QVBoxLayout()
        top = label(tr('VIVID / YOUR PERSONAL CINEMA'))
        top.setStyleSheet("color: #58719b; font-size: 10px; font-weight: 600; letter-spacing: 2px;")
        col.addWidget(top)
        heading = label(tr("Your videos.\nYour pace."))
        heading.setStyleSheet("color: #18315c; font-size: 34px; font-weight: 600; letter-spacing: -0.5px;")
        col.addWidget(heading)
        subtitle = label(tr('Open a favorite. Pick up where you left off.'))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #62769a; font-size: 12px;")
        col.addWidget(subtitle)
        col.addSpacing(5)
        actions = QHBoxLayout()
        actions.addWidget(button(tr('Open video'), "play", open_files, primary=True))
        hint = label(tr('or drop a file here'))
        hint.setStyleSheet("color: #7b8dac; font-size: 11px;")
        actions.addWidget(hint)
        actions.addStretch()
        col.addLayout(actions)
        row.addLayout(col, 1)
        self.art = QLabel()
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art.setFixedWidth(230)
        if not self.pix.isNull():
            self.art.setPixmap(self.pix.scaled(194, 194, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.art.setPixmap(icon("play", "#2563eb").pixmap(130, 130))
        row.addWidget(self.art)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#e8f0ff"))
        grad.setColorAt(.55, QColor("#edf0ff"))
        grad.setColorAt(1, QColor("#e2e9ff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(self.rect()), 16, 16)
        p.setBrush(QColor(255, 255, 255, 75))
        p.drawEllipse(QRectF(self.width() - 350, -160, 490, 490))
        p.setBrush(QColor(130, 168, 255, 23))
        p.drawEllipse(QRectF(self.width() - 310, 90, 380, 380))
        p.end()

    def resizeEvent(self, event):
        self.art.setVisible(self.width() > 650)
        super().resizeEvent(event)


class EmptyState(QFrame):
    def __init__(self, title, description, symbol="film", action=None, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setMinimumHeight(170)
        col = QVBoxLayout(self)
        col.setContentsMargins(24, 22, 24, 22)
        col.setSpacing(9)
        image = QLabel()
        image.setPixmap(icon(symbol, "#8ca5cc").pixmap(36, 36))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addStretch()
        col.addWidget(image)
        title_widget = label(title)
        title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_widget.setStyleSheet("font-size: 15px; font-weight: 600;")
        col.addWidget(title_widget)
        desc = label(description, "muted")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(desc)
        if action:
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(button(tr('Choose files'), "plus", action))
            row.addStretch()
            col.addLayout(row)
        col.addStretch()


class Cover(QWidget):
    def __init__(self, path, entry):
        super().__init__()
        self.path, self.entry = path, entry
        self.pix = QPixmap()
        self.setMinimumHeight(118)
        self.setMaximumHeight(155)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 9, 9)
        p.setClipPath(clip)
        if not self.pix.isNull():
            scaled = self.pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        else:
            color = int(hashlib.sha256(self.path.encode()).hexdigest()[:4], 16) % 100 + 205
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor.fromHsv(color, 95, 100))
            grad.setColorAt(1, QColor.fromHsv((color + 20) % 360, 135, 55))
            p.fillRect(self.rect(), grad)
            p.drawPixmap((self.width() - 38) // 2, (self.height() - 38) // 2, icon("film", "#92a7c6").pixmap(38, 38))
        shade = QLinearGradient(0, self.height() / 2, 0, self.height())
        shade.setColorAt(0, QColor(0, 0, 0, 0))
        shade.setColorAt(1, QColor(0, 0, 0, 115))
        p.fillRect(self.rect(), shade)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("DejaVu Sans", 8))
        p.drawText(10, self.height() - 12, Path(self.path).suffix[1:].upper())
        if self.entry.get("duration"):
            p.drawText(self.rect().adjusted(10, 0, -10, -9), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, timestamp(self.entry["duration"]))
        duration, position = self.entry.get("duration", 0), self.entry.get("position", 0)
        if duration and position:
            p.fillRect(QRectF(0, self.height() - 3, self.width() * min(1, position / duration), 3), QColor("#4b89ff"))
        p.end()


class MediaCard(QFrame):
    activated = Signal(str)
    context = Signal(str, object)

    def __init__(self, path, entry, parent=None):
        super().__init__(parent)
        self.path = path
        self.setObjectName("mediaCard")
        self.setMinimumWidth(180)
        self.setFixedHeight(206)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        bind_text(self, 'setToolTip', path)
        bind_text(self, 'setAccessibleName', (tr('Play') + ' ') + entry.get("name", tr('video')))
        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 10)
        col.setSpacing(8)
        self.cover = Cover(path, entry)
        col.addWidget(self.cover, 1)
        self.name_text = entry.get("name", Path(path).stem)
        name = label(self.name_text)
        self.name_label = name
        name.setStyleSheet("font-weight: 600; font-size: 12px;")
        name.setMinimumWidth(0)
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name.setWordWrap(False)
        col.addWidget(name)
        meta = QHBoxLayout()
        text = (tr('Resume from') + ' ') + timestamp(entry.get("position")) if entry.get("position", 0) >= 3 else tr('Ready to watch')
        small = label(text, "muted")
        small.setStyleSheet("font-size: 10px;")
        meta.addWidget(small, 1)
        if entry.get("favorite"):
            star = QLabel()
            star.setPixmap(icon("star", "#e7a32e").pixmap(14, 14))
            meta.addWidget(star)
        col.addLayout(meta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.path)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.context.emit(self.path, event.globalPos())

    def resizeEvent(self, event):
        if hasattr(self, "name_label"):
            self.name_label.setText(self.name_label.fontMetrics().elidedText(self.name_text, Qt.TextElideMode.ElideRight, max(20, self.width() - 18)))
        super().resizeEvent(event)


class SeekSlider(QSlider):
    """Seek to the clicked position; commit once on release."""
    def _position(self, event):
        position = max(0, min(self.width() - 12, round(event.position().x()) - 6))
        self.setValue(QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), position, max(1, self.width() - 12)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self._position(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self._position(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._position(event)
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ThumbnailSignals(QObject):
    done = Signal(str, str)


class ThumbnailJob(QRunnable):
    def __init__(self, path, destination):
        super().__init__()
        self.path, self.destination = path, destination
        self.signals = ThumbnailSignals()
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def run(self):
        binary = shutil.which("ffmpeg")
        if not binary or self.cancelled.is_set():
            self.signals.done.emit(self.path, "")
            return
        try:
            process = subprocess.Popen([binary, "-nostdin", "-loglevel", "error", "-threads", "1", "-ss", "1", "-i", self.path, "-frames:v", "1", "-vf", "scale=480:270:force_original_aspect_ratio=decrease", "-threads", "1", "-y", str(self.destination)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 12
            while process.poll() is None:
                if self.cancelled.wait(.1) or time.monotonic() > deadline:
                    process.kill()
                    process.wait()
                    break
            success = process.returncode == 0 and self.destination.exists() and not self.cancelled.is_set()
            if not success:
                self.destination.unlink(missing_ok=True)
            self.signals.done.emit(self.path, str(self.destination) if success else "")
        except OSError:
            self.signals.done.emit(self.path, "")
