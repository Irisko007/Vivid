import hashlib
import os
from pathlib import Path
import time

from PySide6.QtCore import QEasingCurve, QEvent, QSettings, QSize, QStandardPaths, Qt, QThreadPool, QTimer, QUrl, QVariantAnimation
from PySide6.QtGui import QAction, QActionGroup, QCursor, QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QScrollArea, QSlider, QStackedWidget,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from .engine import Engine
from .i18n import LANGUAGES, bind_text, retranslate, set_language, tr
from .icons import ASSETS, app_icon, icon
from .storage import Library, SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS, timestamp
from .theme import THEMES, load_fonts, palette, stylesheet
from .widgets import ElidedLabel, EmptyState, FileDialogProxy, Hero, MediaCard, SeekSlider, SidebarButton, SpeedPicker, ThemeChoice, ThumbnailJob, button, label, tool


class Window(QMainWindow):
    def __init__(self, viewer_only=False):
        super().__init__()
        self.viewer_only = viewer_only
        self._chrome_progress = 1.0
        self._chrome_heights = None
        self.library = Library()
        set_language(self.library.settings["language"], QApplication.instance())
        load_fonts(QApplication.instance())
        self.preview_theme = None
        self.preview_language = None
        self.chrome_hidden = False
        self.auto_entered_fullscreen = False
        self.idle_suppressed = False
        self.last_pointer = QCursor.pos()
        self.engine = Engine(self)
        self.current = None
        self.section = "home"
        self.duration = 0
        self.position = 0
        self.playback_speed = 1.0
        self.repeat = False
        self.fullscreen = False
        self.visible_limit = 24
        self.cards = {}
        self.thumb_jobs = {}
        self.thumb_attempted = set()
        self.thumbnails = QThreadPool(self)
        self.thumbnails.setMaxThreadCount(1)
        self.thumbnails.setExpiryTimeout(1000)
        self.cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "vivid/thumbnails"
        self.cache.mkdir(parents=True, exist_ok=True)
        bind_text(self, 'setWindowTitle', tr('Vivid — Video Player'))
        self.setWindowIcon(app_icon())
        self.resize(1100 if viewer_only else 1200, 720 if viewer_only else 820)
        self.setMinimumSize(680 if viewer_only else 950, 420 if viewer_only else 680)
        self.setAcceptDrops(True)
        self.geometry_store = QSettings("Vivid", "Player")
        self.geometry_key = "viewer_geometry" if viewer_only else "geometry"
        geometry = self.geometry_store.value(self.geometry_key)
        if geometry is None and not viewer_only:
            geometry = QSettings("Luma", "Player").value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if viewer_only:
            self.setWindowState(Qt.WindowState.WindowNoState)
        self.build()
        self.chrome_animation = QVariantAnimation(self)
        self.chrome_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.chrome_animation.valueChanged.connect(self.animate_chrome_frame)
        self.chrome_animation.finished.connect(self.finish_chrome_animation)
        self.apply_theme()
        self.shortcuts()
        self.engine.changed.connect(self.on_property)
        self.engine.loaded.connect(self.on_loaded)
        self.engine.ended.connect(self.on_ended)
        self.engine.error.connect(self.show_error)
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(10000)
        self.save_timer.timeout.connect(self.save_position)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.refresh_library)
        self.search.textChanged.connect(lambda _: self.search_timer.start())
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(180)
        self.resize_timer.timeout.connect(self.refresh_library)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.setInterval(2500)
        self.idle_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.idle_timer.timeout.connect(self.hide_player_chrome)
        self.pointer_timer = QTimer(self)
        self.pointer_timer.setInterval(100)
        self.pointer_timer.timeout.connect(self.watch_pointer)
        QApplication.instance().installEventFilter(self)
        self.surface.setMouseTracking(True)
        self.navigate("player" if viewer_only else "home")
        self.update_workspace_chrome()

    def build(self):
        self.root = QWidget()
        self.root.setObjectName("root")
        self.setCentralWidget(self.root)
        root_col = QVBoxLayout(self.root)
        root_col.setContentsMargins(0, 0, 0, 0)
        root_col.setSpacing(0)
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(66)
        h = QHBoxLayout(self.header)
        h.setContentsMargins(24, 0, 24, 0)
        mark = QLabel()
        mark.setPixmap(app_icon().pixmap(32, 32))
        h.addWidget(mark)
        h.addWidget(label("Vivid", "brand"))
        h.addSpacing(18)
        h.addWidget(label(tr('VIDEO PLAYER'), "brandTag"))
        h.addStretch()
        self.search = QLineEdit()
        bind_text(self.search, 'setPlaceholderText', tr('Search your library'))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon("search", "#91a0b8"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setFixedWidth(310)
        h.addWidget(self.search)
        h.addSpacing(14)
        h.addWidget(button(tr('Open file'), "plus", self.open_files, primary=True))
        root_col.addWidget(self.header)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(224)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(12, 22, 12, 16)
        side.setSpacing(5)
        section = label(tr('WORKSPACE'), "eyebrow")
        section.setStyleSheet("font-size: 9px; color: #8997af; padding: 0 10px 12px 10px; letter-spacing: 1px;")
        side.addWidget(section)
        self.nav = {}
        for key, text, sym in [("home", tr('Home'), "home"), ("library", tr('Library'), "library"), ("favorites", tr('Favorites'), "star"), ("player", tr('Now playing'), "play")]:
            w = SidebarButton(text, sym, lambda checked=False, s=key: self.navigate(s))
            w.setCheckable(True)
            w.setIconSize(QSize(19, 19))
            side.addWidget(w)
            self.nav[key] = w
        side.addSpacing(15)
        line = QFrame()
        line.setObjectName("sidebarDivider")
        line.setFixedHeight(1)
        side.addWidget(line)
        side.addSpacing(10)
        side.addWidget(SidebarButton(tr('Add folder'), "folder", self.open_folder))
        side.addStretch()
        self.now_playing = SidebarButton("", "film", lambda: self.navigate("player"), tr('Now playing'))
        self.now_playing.setObjectName("currentTrack")
        self.now_playing.setVisible(False)
        side.addWidget(self.now_playing)
        side.addSpacing(18)
        app_section = label(tr('APPLICATION'), "eyebrow")
        app_section.setStyleSheet("font-size: 9px; padding-left: 13px; letter-spacing: 1px;")
        side.addWidget(app_section)
        side.addWidget(SidebarButton(tr('Settings'), "settings", self.settings_dialog))
        side.addWidget(SidebarButton(tr('Keyboard shortcuts'), "keyboard", self.help_dialog))
        side.addSpacing(16)
        foot = label("VIVID 1.3  ·  LINUX", "eyebrow")
        foot.setStyleSheet("color: #98a5bb; font-size: 9px; padding-left: 11px; letter-spacing: 1px;")
        side.addWidget(foot)
        body.addWidget(self.sidebar)
        self.pages = QStackedWidget()
        self.library_page = QWidget()
        self.library_page.setObjectName("page")
        page_col = QVBoxLayout(self.library_page)
        page_col.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.library_content = QWidget()
        self.library_content.setObjectName("page")
        self.library_layout = QVBoxLayout(self.library_content)
        self.library_layout.setContentsMargins(32, 27, 32, 24)
        self.library_layout.setSpacing(22)
        self.scroll.setWidget(self.library_content)
        page_col.addWidget(self.scroll)
        self.pages.addWidget(self.library_page)
        self.build_player()
        body.addWidget(self.pages, 1)
        root_col.addLayout(body, 1)
        self.footer = QFrame()
        self.footer.setObjectName("footer")
        self.footer.setFixedHeight(32)
        f = QHBoxLayout(self.footer)
        f.setContentsMargins(22, 0, 22, 0)
        self.status = label(tr('Ready to watch'), "muted")
        self.status.setStyleSheet("font-size: 10px;")
        f.addWidget(self.status, 1)
        self.footer_right = label(tr('Local files · Your space'), "muted")
        self.footer_right.setStyleSheet("font-size: 10px;")
        f.addWidget(self.footer_right)
        root_col.addWidget(self.footer)

    def build_player(self):
        self.player_page = QWidget()
        self.player_page.setObjectName("page")
        col = QVBoxLayout(self.player_page)
        self.player_layout = col
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(7)
        self.player_titlebar = QWidget()
        title_row = QHBoxLayout(self.player_titlebar)
        title_row.setContentsMargins(9, 2, 9, 4)
        titles = QVBoxLayout()
        self.video_title = ElidedLabel(tr('Choose a video'))
        self.video_title.setObjectName("sectionTitle")
        self.video_title.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.video_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        titles.addWidget(self.video_title)
        title_row.addLayout(titles, 1)
        self.favorite_btn = tool("star", tr('Add to favorites'), self.toggle_favorite)
        title_row.addWidget(self.favorite_btn)
        title_row.addWidget(tool("subtitle", tr('Subtitles'), self.subtitle_menu))
        title_row.addWidget(tool("audio", tr('Audio track'), self.audio_menu))
        title_row.addWidget(tool("more", tr('More'), self.more_menu))
        col.addWidget(self.player_titlebar)
        self.player_body = QHBoxLayout()
        self.player_body.setSpacing(16)
        self.video_stack = QStackedWidget()
        self.video_stack.setMinimumSize(320, 200)
        empty = QFrame()
        empty.setStyleSheet("background: #101a2c; border-radius: 12px;")
        v = QVBoxLayout(empty)
        v.addStretch()
        image = QLabel()
        image.setPixmap(app_icon().pixmap(90, 90))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(image)
        txt = label(tr('Ready when you are'))
        txt.setStyleSheet("color: #e8efff; font-size: 22px; font-weight: 600;")
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(txt)
        txt = label(tr('Drop a video here or choose a file'))
        txt.setStyleSheet("color: #889bbd;")
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(txt)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button(tr('Open video'), "plus", self.open_files, primary=True))
        row.addStretch()
        v.addSpacing(15)
        v.addLayout(row)
        v.addStretch()
        self.video_stack.addWidget(empty)
        self.surface = QWidget()
        self.surface.setStyleSheet("background: black;")
        self.surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.surface.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_stack.addWidget(self.surface)
        self.player_body.addWidget(self.video_stack, 1)
        self.queue_panel = QFrame()
        self.queue_panel.setObjectName("panel")
        self.queue_panel.setFixedWidth(245)
        q = QVBoxLayout(self.queue_panel)
        q.setContentsMargins(12, 16, 12, 12)
        qh = QHBoxLayout()
        qh.addWidget(label(tr('Queue'), "sectionTitle"), 1)
        qh.addWidget(tool("plus", tr('Add videos to queue'), self.append_files, size=28))
        qh.addWidget(tool("close", tr('Hide queue'), lambda: self.queue_panel.hide(), size=28))
        q.addLayout(qh)
        self.queue_list = QListWidget()
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.queue_context)
        self.queue_list.itemDoubleClicked.connect(lambda item: self.play(item.data(Qt.ItemDataRole.UserRole)))
        q.addWidget(self.queue_list, 1)
        q.addWidget(label(tr('Double-click to play'), "muted"))
        q.addWidget(button(tr('Clear queue'), "trash", self.clear_queue))
        self.player_body.addWidget(self.queue_panel)
        self.queue_panel.hide()
        col.addLayout(self.player_body, 1)
        self.controls = QFrame()
        self.controls.setObjectName("controls")
        controls = QVBoxLayout(self.controls)
        controls.setContentsMargins(12, 9, 12, 9)
        controls.setSpacing(5)
        timeline = QHBoxLayout()
        self.elapsed = label("0:00", "muted")
        self.elapsed.setMinimumWidth(40)
        timeline.addWidget(self.elapsed)
        self.seek_slider = SeekSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.seek_slider.setRange(0, 10000)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderReleased.connect(self.seek_absolute)
        self.seek_slider.valueChanged.connect(self.preview_seek)
        timeline.addWidget(self.seek_slider, 1)
        self.total = label("0:00", "muted")
        self.total.setMinimumWidth(40)
        timeline.addWidget(self.total)
        controls.addLayout(timeline)
        bottom = QGridLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(0)
        left_wing = QWidget()
        left = QHBoxLayout(left_wing)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(5)
        self.speed_combo = SpeedPicker()
        self.speed_combo.currentIndexChanged.connect(lambda _: self.set_speed(self.speed_combo.currentData()))
        left.addWidget(self.speed_combo)
        self.fit_btn = tool("aspect", tr('Video size · Fit / Fill / Stretch'), self.fit_menu, size=32)
        left.addWidget(self.fit_btn)
        left.addStretch()
        bottom.addWidget(left_wing, 0, 0)
        self.transport_group = QWidget()
        self.transport_group.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.transport_group.setFixedWidth(340)
        row = QHBoxLayout(self.transport_group)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(tool("previous", tr('Previous video · Ctrl+←'), lambda: self.next_video(-1), size=32))
        row.addWidget(tool("rewind", tr('Back 10 seconds · ←'), lambda: self.seek(-10), size=32))
        self.play_btn = tool("play", tr('Play / pause · Space'), self.toggle_pause, color="#ffffff", size=40)
        self.play_btn.setObjectName("playButton")
        self.play_btn.setStyleSheet("")
        row.addWidget(self.play_btn)
        row.addWidget(tool("forward", tr('Forward 10 seconds · →'), lambda: self.seek(10), size=32))
        row.addWidget(tool("next", tr('Next video · Ctrl+→'), self.next_video, size=32))
        row.addSpacing(10)
        self.mute_btn = tool("volume", tr('Sound · M'), lambda: self.engine.command("cycle", "mute"), size=28)
        row.addWidget(self.mute_btn)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.library.settings.get("volume", 75)))
        self.volume_slider.setFixedWidth(70)
        bind_text(self.volume_slider, 'setToolTip', tr('Volume'))
        self.volume_slider.valueChanged.connect(self.set_volume)
        row.addWidget(self.volume_slider)
        bottom.addWidget(self.transport_group, 0, 1, Qt.AlignmentFlag.AlignCenter)
        right_wing = QWidget()
        right = QHBoxLayout(right_wing)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)
        right.addStretch()
        self.repeat_btn = tool("repeat", tr('Repeat queue'), self.toggle_repeat, size=32)
        right.addWidget(self.repeat_btn)
        self.queue_btn = tool("queue", tr('Play queue · Ctrl+P'), self.toggle_queue, size=32)
        right.addWidget(self.queue_btn)
        self.fs_btn = tool("fullscreen", tr('Fullscreen · F'), self.toggle_fullscreen, size=32)
        right.addWidget(self.fs_btn)
        bottom.addWidget(right_wing, 0, 2)
        bottom.setColumnStretch(0, 1)
        bottom.setColumnStretch(2, 1)
        bottom.setColumnMinimumWidth(0, 114)
        bottom.setColumnMinimumWidth(2, 114)
        controls.addLayout(bottom)
        col.addWidget(self.controls)
        self.pages.addWidget(self.player_page)

    def apply_theme(self):
        name = self.preview_theme or self.library.settings.get("theme", "light")
        name = name if name in THEMES else "light"
        self.dark = THEMES[name]["dark"]
        self.colors = THEMES[name]["colors"]
        application = QApplication.instance()
        application.setPalette(palette(name))
        application.setStyleSheet(stylesheet(name))
        for w in self.findChildren(QPushButton):
            symbol = getattr(w, "_icon_symbol", None)
            if symbol:
                role = getattr(w, "_icon_role", "muted")
                w.setIcon(icon(symbol, "#ffffff" if role == "white" else self.colors.get(role, self.colors["muted"])))
        for key, w in self.nav.items():
            symbol = {"home": "home", "library": "library", "favorites": "star", "player": "play"}[key]
            w.setIcon(icon(symbol, self.colors["blue"] if key == self.section else self.colors["muted"]))
            w.text_label.setStyleSheet(f"color: {self.colors['blue'] if key == self.section else self.colors['muted']}; font-weight: 500;")
        self.update_favorite()
        self.play_btn.setIcon(icon("play" if self.engine.props.get("pause", True) else "pause", "#ffffff"))
        self.mute_btn.setIcon(icon("mute" if self.engine.props.get("mute") else "volume", self.colors["muted"]))
        self.repeat_btn.setIcon(icon("repeat", self.colors["blue"] if self.repeat else self.colors["muted"]))
        self.fs_btn.setIcon(icon("collapse" if self.fullscreen else "fullscreen", self.colors["muted"]))

    def update_workspace_chrome(self):
        visible = not (self.viewer_only or self.fullscreen or self.chrome_hidden)
        for widget in (self.header, self.sidebar, self.footer):
            widget.setVisible(visible)

    def open_workspace(self):
        self.viewer_only = False
        self.geometry_key = "geometry"
        self.setMinimumSize(950, 680)
        self.navigate("library")
        self.update_workspace_chrome()

    def navigate(self, section):
        if self.viewer_only and section != "player":
            self.viewer_only = False
            self.geometry_key = "geometry"
            self.setMinimumSize(950, 680)
        if section != "player" and hasattr(self, "idle_timer"):
            if self.fullscreen:
                self.exit_fullscreen()
            self.idle_suppressed = False
            self.reveal_player_chrome()
            self.idle_timer.stop()
            self.pointer_timer.stop()
        self.section = section
        for key, w in self.nav.items():
            w.setChecked(key == section)
        self.pages.setCurrentIndex(1 if section == "player" else 0)
        self.search.setEnabled(section != "player")
        if section != "player":
            self.refresh_library()
        self.apply_theme()
        self.update_workspace_chrome()
        if section == "player" and hasattr(self, "idle_timer"):
            self.note_activity()

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                Window.clear_layout(item.layout())

    def refresh_library(self):
        if self.section == "player":
            return
        self.clear_layout(self.library_layout)
        self.cards = {}
        home = self.section == "home"
        query = self.search.text().strip()
        title_row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(7)
        heading = tr('Welcome') if home else (tr('Favorites') if self.section == "favorites" else tr('Your library'))
        titles.addWidget(label(heading, "heading"))
        titles.addWidget(label(tr('A good video starts with a click.') if home else tr('All your videos in one place.'), "muted"))
        title_row.addLayout(titles, 1)
        title_row.addWidget(label(tr('Personal space'), "badge"))
        self.library_layout.addLayout(title_row)
        if home and not query:
            self.library_layout.addWidget(Hero(self.open_files))
            actions = QHBoxLayout()
            actions.setSpacing(14)
            for title, description, symbol, callback in [(tr('Open file'), tr('MP4, MKV, WebM and more'), "file", self.open_files), (tr('Add folder'), tr('Collect videos in your library'), "folder", self.open_folder)]:
                panel = QFrame()
                panel.setObjectName("panel")
                r = QHBoxLayout(panel)
                r.setContentsMargins(15, 13, 14, 13)
                r.addWidget(tool(symbol, title, callback, color="#2563eb", size=38))
                t = QVBoxLayout()
                t.setSpacing(4)
                name = label(title)
                name.setStyleSheet("font-size: 12px; font-weight: 600;")
                t.addWidget(name)
                small = label(description, "muted")
                small.setStyleSheet("font-size: 10px;")
                t.addWidget(small)
                r.addLayout(t, 1)
                r.addWidget(tool("chevron", title, callback, size=28))
                actions.addWidget(panel, 1)
            self.library_layout.addLayout(actions)
        entries = self.library.recent(self.section == "favorites", query)
        title = QHBoxLayout()
        title.addWidget(label(tr('Search results') if query else (tr('Recent videos') if home else tr('Videos')), "sectionTitle"))
        count = label(str(len(entries)), "badge")
        title.addWidget(count)
        title.addStretch()
        if home:
            title.addWidget(button(tr('Full library →'), callback=lambda: self.navigate("library")))
        self.library_layout.addLayout(title)
        if not entries:
            if query:
                empty = EmptyState(tr('No videos found'), tr('Try another name or clear the search.'), "search")
            elif self.section == "favorites":
                empty = EmptyState(tr('Your favorites, always here'), tr('Click the star while watching to keep a video here.'), "star")
            else:
                empty = EmptyState(tr('Your videos will appear here'), tr('Open a video. Vivid remembers it and your playback position.'), action=self.open_files)
            self.library_layout.addWidget(empty)
        else:
            grid = QGridLayout()
            grid.setSpacing(16)
            columns = 3 if self.pages.width() > 850 else 2
            limit = 6 if home else self.visible_limit
            for i, (path, entry) in enumerate(entries[:limit]):
                card = MediaCard(path, entry)
                card.activated.connect(self.play)
                card.context.connect(self.card_context)
                grid.addWidget(card, i // columns, i % columns)
                self.cards[path] = card
                self.request_thumbnail(path)
            for i in range(columns):
                grid.setColumnStretch(i, 1)
            self.library_layout.addLayout(grid)
            if not home and len(entries) > limit:
                self.library_layout.addWidget(button(tr('Show more'), callback=self.load_more))
        self.library_layout.addStretch()
        note = QHBoxLayout()
        note.addWidget(label("●", "muted"))
        text = label(tr('Your files stay on this device'), "muted")
        text.setStyleSheet("font-size: 10px;")
        note.addWidget(text)
        note.addStretch()
        text = label(tr('MADE FOR LINUX'), "eyebrow")
        text.setStyleSheet("color: #98a5bb; font-size: 9px; letter-spacing: 1px;")
        note.addWidget(text)
        self.library_layout.addLayout(note)

    def load_more(self):
        self.visible_limit += 24
        self.refresh_library()

    def request_thumbnail(self, path):
        try:
            stat = Path(path).stat()
        except OSError:
            return
        key = hashlib.sha256(f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()
        destination = self.cache / (key + ".jpg")
        if destination.exists():
            self.set_thumbnail(path, str(destination))
        elif path not in self.thumb_jobs and path not in self.thumb_attempted:
            job = ThumbnailJob(path, destination)
            job.signals.done.connect(self.set_thumbnail)
            self.thumb_jobs[path] = job
            self.thumb_attempted.add(path)
            self.thumbnails.start(job)

    def set_thumbnail(self, path, image):
        self.thumb_jobs.pop(path, None)
        if image and path in self.cards:
            self.cards[path].cover.pix = QPixmap(image)
            self.cards[path].cover.update()

    def choose_files(self):
        extensions = " ".join("*" + ext for ext in sorted(VIDEO_EXTENSIONS))
        dialog = self.file_dialog(tr('Open video'), tr('Open'))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters([tr("Videos ({extensions})", extensions=extensions), tr('All files (*)')])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selectedFiles()
        return []

    def file_dialog(self, title, accept):
        self.note_activity()
        dialog = QFileDialog(self, title)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.vivid_proxy = FileDialogProxy(dialog)
        dialog.setProxyModel(dialog.vivid_proxy)
        dialog.setViewMode(QFileDialog.ViewMode.Detail)
        dialog.setDirectory(str(Path(self.current).parent) if self.current else str(Path.home()))
        locations = [QStandardPaths.StandardLocation.HomeLocation, QStandardPaths.StandardLocation.DesktopLocation, QStandardPaths.StandardLocation.DownloadLocation, QStandardPaths.StandardLocation.MoviesLocation]
        urls = []
        for location in locations:
            path = QStandardPaths.writableLocation(location)
            if not path or not Path(path).is_dir():
                alternatives = {
                    QStandardPaths.StandardLocation.DesktopLocation: ["Desktop", "Рабочий стол"],
                    QStandardPaths.StandardLocation.DownloadLocation: ["Downloads", "Загрузки"],
                    QStandardPaths.StandardLocation.MoviesLocation: ["Videos", "Видео"],
                }.get(location, [])
                path = next((str(Path.home() / name) for name in alternatives if (Path.home() / name).is_dir()), "")
            if path and Path(path).is_dir() and QUrl.fromLocalFile(path) not in urls:
                urls.append(QUrl.fromLocalFile(path))
        dialog.setSidebarUrls(urls)
        for role, caption in [(QFileDialog.DialogLabel.LookIn, tr('Folder:')), (QFileDialog.DialogLabel.FileName, tr('Name:')), (QFileDialog.DialogLabel.FileType, tr('Files of type:')), (QFileDialog.DialogLabel.Accept, accept), (QFileDialog.DialogLabel.Reject, tr('Cancel'))]:
            dialog.setLabelText(role, caption)
        screen = self.screen().availableGeometry()
        dialog.resize(min(880, screen.width() - 60), min(570, screen.height() - 70))
        dialog.setMinimumSize(660, 420)
        sidebar = dialog.findChild(QListView, "sidebar")
        if sidebar:
            sidebar.setMinimumWidth(170)
            sidebar.setMaximumWidth(210)
        splitter = dialog.findChild(QSplitter, "splitter")
        if splitter:
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([180, 660])
        return dialog

    def open_files(self):
        paths = self.choose_files()
        if paths:
            self.add_files(paths, play=True)

    def append_files(self):
        paths = self.choose_files()
        if paths:
            self.add_files(paths)

    def add_files(self, paths, play=False):
        added = self.library.add(paths)
        for path in added:
            if path not in self.library.queue:
                self.library.queue.append(path)
        self.persist()
        self.refresh_queue()
        if added and play:
            self.play(added[0])
        else:
            self.refresh_library()
        bind_text(self.status, 'setText', tr("Videos added: {count}", count=len(added)) if added else tr('No supported videos found'))

    def open_folder(self):
        dialog = self.file_dialog(tr('Add a video folder'), tr('Add folder'))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setNameFilter(tr('Folders'))
        dialog.setLabelText(QFileDialog.DialogLabel.FileName, tr('Selected folder:'))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        path = dialog.selectedFiles()[0]
        # Only the selected directory is indexed; subdirectories are intentional separate imports.
        try:
            paths = [str(p) for p in Path(path).iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
            self.add_files(paths)
        except OSError as e:
            self.show_error((tr('Could not read folder:') + ' ') + str(e))

    def play(self, path):
        if not Path(path).is_file():
            self.show_error(tr("File is no longer available:\n{path}", path=path))
            return
        added = self.library.add([path])
        if not added:
            return
        self.save_position()
        self.current = path
        if path not in self.library.queue:
            self.library.queue.append(path)
        entry = self.library.entries[path]
        position = entry.get("position", 0) if self.library.settings.get("resume") else 0
        if position >= max(0, entry.get("duration", 0) - 3):
            position = 0
        self.position = self.duration = 0
        bind_text(self.elapsed, 'setText', "0:00")
        bind_text(self.total, 'setText', "0:00")
        self.seek_slider.setValue(0)
        self.seek_slider.setEnabled(False)
        bind_text(self.video_title, 'setText', entry["name"].replace("_", " "))
        bind_text(self, 'setWindowTitle', entry["name"].replace("_", " ") + " — Vivid")
        bind_text(self.video_title, 'setToolTip', path)
        bind_text(self.now_playing, 'setText', entry["name"].replace("_", " "))
        bind_text(self.now_playing, 'setToolTip', path)
        self.now_playing.show()
        self.video_stack.setCurrentIndex(1)
        self.navigate("player")
        self.update_favorite()
        self.refresh_queue()
        if self.engine.start(int(self.surface.winId()), self.library.settings):
            bind_text(self.status, 'setText', tr('Opening video…'))
            self.engine.load(path, position)
        else:
            self.current = None
            self.video_stack.setCurrentIndex(0)

    def on_loaded(self):
        if self.current:
            self.library.entries[self.current]["played"] = time.time()
            self.engine.set("speed", self.playback_speed)
            self.set_video_fit(self.library.settings.get("video_fit", "fit"), save=False)
            bind_text(self.status, 'setText', tr('Playing'))
            self.persist()

    def on_property(self, name, value):
        if name == "time-pos":
            self.position = float(value or 0)
            if not self.seek_slider.isSliderDown():
                bind_text(self.elapsed, 'setText', timestamp(self.position))
                self.seek_slider.blockSignals(True)
                self.seek_slider.setValue(round(self.position / self.duration * 10000) if self.duration else 0)
                self.seek_slider.blockSignals(False)
        elif name == "duration":
            self.duration = float(value or 0)
            bind_text(self.total, 'setText', timestamp(self.duration))
            self.seek_slider.setEnabled(self.duration > 0)
            if self.current:
                self.library.entries[self.current]["duration"] = self.duration
        elif name == "pause":
            self.play_btn.setIcon(icon("play" if value else "pause", "#ffffff"))
            bind_text(self.status, 'setText', tr('Paused') if value else tr('Playing'))
            if value:
                self.save_timer.stop()
                self.save_position()
                self.idle_timer.stop()
                self.pointer_timer.stop()
                self.reveal_player_chrome()
            else:
                self.save_timer.start()
                self.idle_suppressed = False
                self.note_activity()
            bind_text(self.now_playing.secondary_label, 'setText', tr('Paused') if value else tr('Now playing'))
        elif name == "speed" and value:
            if abs(value - self.playback_speed) < .001:
                self.speed_combo.setValue(value, emit=False)
        elif name == "volume" and value is not None:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(round(value))
            self.volume_slider.blockSignals(False)
        elif name == "mute":
            self.mute_btn.setIcon(icon("mute" if value else "volume", self.colors["muted"]))
        elif name in {"hwdec-current", "video-params"}:
            params = self.engine.props.get("video-params") or {}
            hw = self.engine.props.get("hwdec-current")
            resolution = f"{params.get('w', '')} × {params.get('h', '')}" if params.get("w") else ""
            bind_text(self.footer_right, 'setText', "  ·  ".join(x for x in [resolution, f"GPU · {hw}" if hw and hw != "no" else tr("Software decoding")] if x))

    def save_position(self):
        if self.current and self.current in self.library.entries and self.duration > 0:
            self.library.entries[self.current]["position"] = 0 if self.duration and self.position >= self.duration - 2 else self.position
            self.library.entries[self.current]["duration"] = self.duration
        self.persist()

    def persist(self):
        try:
            self.library.save()
        except OSError as e:
            bind_text(self.status, 'setText', (tr('Could not save library:') + ' ') + str(e))

    def toggle_pause(self):
        if not self.current:
            self.open_files()
        elif self.engine.props.get("eof-reached"):
            self.engine.command("seek", 0, "absolute")
            self.engine.set("pause", False)
        else:
            self.engine.command("cycle", "pause")

    def seek(self, seconds):
        if self.current:
            self.engine.command("seek", seconds, "relative")

    def seek_absolute(self):
        if self.duration:
            self.engine.command("seek", self.seek_slider.value() / 10000 * self.duration, "absolute+exact")

    def preview_seek(self, value):
        if self.duration:
            bind_text(self.elapsed, 'setText', timestamp(value / 10000 * self.duration))
        # Keyboard and groove clicks do not emit sliderReleased.
        if self.duration and not self.seek_slider.isSliderDown():
            self.seek_absolute()

    def set_volume(self, volume):
        self.library.settings["volume"] = volume
        self.engine.set("volume", volume)

    def set_speed(self, value):
        self.playback_speed = value
        self.engine.set("speed", value)

    def next_video(self, direction=1):
        if isinstance(direction, bool):
            direction = 1
        queue = self.library.queue
        if not queue:
            return
        index = queue.index(self.current) if self.current in queue else -1
        target = index + direction
        if self.repeat:
            target %= len(queue)
        while 0 <= target < len(queue):
            if Path(queue[target]).is_file():
                self.play(queue[target])
                return
            target += direction

    def on_ended(self):
        self.position = 0
        self.save_position()
        if self.library.settings.get("autoplay"):
            self.next_video()
        elif self.repeat and self.current:
            self.play(self.current)

    def toggle_repeat(self):
        self.repeat = not self.repeat
        self.repeat_btn.setIcon(icon("repeat", self.colors["blue"] if self.repeat else self.colors["muted"]))
        self.set_button_active(self.repeat_btn, self.repeat)
        bind_text(self.repeat_btn, 'setToolTip', tr('Queue repeat enabled') if self.repeat else tr('Repeat queue'))

    def toggle_queue(self):
        self.queue_panel.setVisible(not self.queue_panel.isVisible())
        self.set_button_active(self.queue_btn, self.queue_panel.isVisible())
        self.refresh_queue()

    def refresh_queue(self):
        self.queue_list.clear()
        for path in self.library.queue:
            entry = self.library.entries.get(path, {})
            item = QListWidgetItem(icon("play" if path == self.current else "film", "#2563eb" if path == self.current else "#94a3b8"), entry.get("name", Path(path).stem))
            item.setData(Qt.ItemDataRole.UserRole, path)
            bind_text(item, 'setToolTip', path)
            self.queue_list.addItem(item)
            if path == self.current:
                self.queue_list.setCurrentItem(item)

    def clear_queue(self):
        self.library.queue = [self.current] if self.current else []
        self.refresh_queue()
        self.persist()

    def queue_context(self, point):
        item = self.queue_list.itemAt(point)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction(tr('Play'), lambda: self.play(path))
        menu.addAction(tr('Remove from queue'), lambda: self.remove_from_queue(path))
        menu.exec(self.queue_list.mapToGlobal(point))

    def remove_from_queue(self, path):
        self.library.queue = [p for p in self.library.queue if p != path]
        self.refresh_queue()
        self.persist()

    def toggle_favorite(self, path=None):
        if not isinstance(path, str):
            path = self.current
        if path and path in self.library.entries:
            e = self.library.entries[path]
            e["favorite"] = not e.get("favorite", False)
            self.persist()
            self.update_favorite()
            self.refresh_library()

    def update_favorite(self):
        favorite = self.library.entries.get(self.current, {}).get("favorite", False)
        self.set_button_active(self.favorite_btn, favorite)
        self.favorite_btn.setIcon(icon("star", "#e7a32e" if favorite else self.colors["muted"]))
        bind_text(self.favorite_btn, 'setToolTip', tr('Remove from favorites') if favorite else tr('Add to favorites'))

    def card_context(self, path, point):
        menu = QMenu(self)
        menu.addAction(icon("play"), tr('Play'), lambda: self.play(path))
        menu.addAction(icon("star"), tr('Toggle favorite'), lambda: self.toggle_favorite(path))
        menu.addAction(icon("queue"), tr('Add to queue'), lambda: self.add_files([path]))
        menu.addAction(icon("folder"), tr('Open containing folder'), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent))))
        menu.addSeparator()
        menu.addAction(tr('Remove from library'), lambda: self.remove_library_entry(path))
        menu.exec(point)

    def remove_library_entry(self, path):
        if path == self.current:
            self.engine.command("stop")
            self.current = None
            self.position = self.duration = 0
            self.save_timer.stop()
            self.video_stack.setCurrentIndex(0)
            bind_text(self.video_title, 'setText', tr('Choose a video'))
            self.now_playing.hide()
        self.library.entries.pop(path, None)
        self.remove_from_queue(path)
        self.refresh_library()

    def track_menu(self, kind, widget):
        if not self.current:
            return
        menu = QMenu(self)
        group = QActionGroup(menu)
        prop = "sid" if kind == "sub" else "aid"
        tracks = [t for t in (self.engine.props.get("track-list") or []) if t.get("type") == kind]
        if kind == "sub":
            off = menu.addAction(tr('Off'))
            off.setCheckable(True)
            off.setChecked(not any(t.get("selected") for t in tracks))
            group.addAction(off)
            off.triggered.connect(lambda: self.engine.set(prop, "no"))
        for track in tracks:
            name = " · ".join(str(track[k]) for k in ("title", "lang", "codec") if track.get(k)) or tr("Track {number}", number=track["id"])
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(bool(track.get("selected")))
            group.addAction(action)
            action.triggered.connect(lambda checked=False, tid=track["id"]: self.engine.set(prop, tid))
        if not tracks and kind == "audio":
            menu.addAction(tr('No audio tracks')).setEnabled(False)
        if kind == "sub":
            menu.addSeparator()
            menu.addAction(tr('Load subtitle file…'), self.open_subtitles)
        menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))

    def subtitle_menu(self):
        self.track_menu("sub", self.favorite_btn)

    def audio_menu(self):
        self.track_menu("audio", self.favorite_btn)

    def open_subtitles(self):
        if self.current:
            dialog = self.file_dialog(tr('Load subtitles'), tr('Load'))
            dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            dialog.setNameFilter(tr('Subtitles (*.srt *.ass *.ssa *.vtt *.sub)'))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.engine.command("sub-add", dialog.selectedFiles()[0], "select")

    def more_menu(self):
        menu = QMenu(self)
        menu.addAction(tr('Open video… · Ctrl+O'), self.open_files)
        if self.viewer_only:
            menu.addAction(tr('Open library · Ctrl+L'), self.open_workspace)
        menu.addAction(tr('Settings'), self.settings_dialog)
        menu.addSeparator()
        menu.addAction(tr('Save frame · Ctrl+S'), self.screenshot)
        menu.addAction(tr('Video information'), self.file_info)
        menu.addSeparator()
        menu.addAction(tr('Open containing folder'), self.open_current_folder)
        menu.exec(self.favorite_btn.mapToGlobal(self.favorite_btn.rect().bottomLeft()))

    def screenshot(self):
        if not self.current:
            return
        directory = Path.home() / "Pictures/Vivid"
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{Path(self.current).stem}-{time.time_ns()}.png"
        self.engine.command("screenshot-to-file", str(destination), "subtitles")
        bind_text(self.status, 'setText', (tr('Frame saved:') + ' ') + str(destination))

    def open_current_folder(self):
        if self.current:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.current).parent)))

    def file_info(self):
        if not self.current:
            return
        params = self.engine.props.get("video-params") or {}
        try:
            size = f"{Path(self.current).stat().st_size / 1024**2:.1f} " + tr("MB")
        except OSError:
            size = tr('Unavailable')
        text = tr("File: {path}\n\nDuration: {duration}\nSize: {size}\nResolution: {width} × {height}\nDecoding: {decoder}", path=self.current, duration=timestamp(self.duration), size=size, width=params.get("w", "—"), height=params.get("h", "—"), decoder=self.engine.props.get("hwdec-current") or tr("software"))
        QMessageBox.information(self, tr('Video information'), text)

    def settings_dialog(self):
        self.note_activity()
        dialog = QDialog(self)
        bind_text(dialog, 'setWindowTitle', tr('Vivid settings'))
        dialog.setMinimumSize(580, 450)
        dialog.resize(640, min(740, self.screen().availableGeometry().height() - 90))
        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(20, 20, 20, 20)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(6, 4, 6, 12)
        col.setSpacing(12)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        col.addWidget(label(tr('Settings'), "heading"))
        col.addWidget(label(tr('Preview a theme. Press Save to keep your changes.'), "muted"))
        language_row = QHBoxLayout()
        language_row.addWidget(label(tr("Interface language")))
        language_combo = QComboBox()
        for code, (name, _) in LANGUAGES.items():
            language_combo.addItem(name, code)
        language_combo.setCurrentIndex(language_combo.findData(self.library.settings["language"]))
        bind_text(language_combo, 'setAccessibleName', tr("Interface language"))
        language_row.addWidget(language_combo, 1)
        col.addLayout(language_row)
        language_note = label(tr("Language previews immediately. Press Save to keep it."), "muted")
        language_note.setWordWrap(True)
        col.addWidget(language_note)
        def preview_language(_):
            self.preview_language = language_combo.currentData()
            set_language(self.preview_language, QApplication.instance())
            retranslate(self)
            self.refresh_library()
            self.on_property("hwdec-current", self.engine.props.get("hwdec-current"))
        language_combo.currentIndexChanged.connect(preview_language)
        themes = QGridLayout()
        themes.setSpacing(9)
        self.theme_choices = {}
        selected_theme = self.library.settings.get("theme", "light")
        def preview(name):
            self.preview_theme = name
            for key, choice in self.theme_choices.items():
                choice.setProperty("selected", key == name)
            self.apply_theme()
            self.refresh_library()
        for i, (key, data) in enumerate(THEMES.items()):
            choice = ThemeChoice(data["name"], data["colors"], lambda checked=False, k=key: preview(k))
            choice.setProperty("selected", key == selected_theme)
            self.theme_choices[key] = choice
            themes.addWidget(choice, i // 3, i % 3)
        col.addLayout(themes)
        checks = {}
        for key, text, explanation in [("hwdec", tr('Hardware decoding'), tr('Use the GPU when the format and driver support it.')), ("resume", tr('Remember playback position'), tr('Continue where you left off.')), ("autoplay", tr('Play next automatically'), tr('Continue with the next video in the queue.')), ("auto_fullscreen", tr('Fullscreen when idle'), tr('Applies to library playback. Files opened externally stay windowed.'))]:
            checkbox = QCheckBox(text)
            bind_text(checkbox, "setText", text)
            checkbox.setChecked(bool(self.library.settings.get(key)))
            checks[key] = checkbox
            col.addWidget(checkbox)
            description = label(explanation, "muted")
            description.setWordWrap(True)
            description.setStyleSheet("font-size: 11px; padding-left: 28px;")
            col.addWidget(description)
        col.addSpacing(8)
        col.addWidget(button(tr('Open data folder'), "folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.library.root)))))
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(button(tr('Cancel'), callback=dialog.reject))
        def save_settings():
            previous = dict(self.library.settings)
            self.library.settings.update({k: c.isChecked() for k, c in checks.items()})
            self.library.settings["theme"] = self.preview_theme or selected_theme
            self.library.settings["language"] = language_combo.currentData()
            try:
                self.library.save()
            except OSError as error:
                self.library.settings = previous
                QMessageBox.warning(dialog, "Vivid", tr("Could not save settings: {error}", error=str(error)))
                return
            self.engine.set("hwdec", "auto-safe" if checks["hwdec"].isChecked() else "no")
            dialog.accept()
        actions.addWidget(button(tr('Save'), "check", save_settings, primary=True))
        outer.addLayout(actions)
        dialog.exec()
        self.preview_theme = None
        self.preview_language = None
        self.theme_choices = {}
        set_language(self.library.settings["language"], QApplication.instance())
        retranslate(self)
        self.on_property("hwdec-current", self.engine.props.get("hwdec-current"))
        self.apply_theme()
        self.refresh_library()
        self.note_activity()

    def fit_menu(self):
        menu = QMenu(self)
        group = QActionGroup(menu)
        modes = [("fit", tr('Fit · Keep aspect ratio')), ("fill", tr('Fill · Crop edges')), ("stretch", tr('Stretch · Full frame without bars'))]
        for key, caption in modes:
            action = menu.addAction(caption)
            action.setCheckable(True)
            action.setChecked(self.library.settings.get("video_fit", "fit") == key)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, k=key: self.set_video_fit(k))
        menu.exec(self.fit_btn.mapToGlobal(self.fit_btn.rect().topLeft()))

    def set_video_fit(self, mode, save=True):
        if mode not in {"fit", "fill", "stretch"}:
            mode = "fit"
        self.library.settings["video_fit"] = mode
        self.engine.set("keepaspect", mode != "stretch")
        self.engine.set("panscan", 1.0 if mode == "fill" else 0.0)
        self.engine.set("video-zoom", 0.0)
        self.engine.set("video-unscaled", "no")
        captions = {"fit": tr('Fit'), "fill": tr('Fill with cropping'), "stretch": tr('Stretch without bars')}
        bind_text(self.fit_btn, 'setToolTip', (tr('Video size:') + ' ') + captions[mode])
        self.set_button_active(self.fit_btn, mode != "fit")
        if save:
            self.persist()

    def help_dialog(self):
        lines = [tr("Open video… · Ctrl+O"), tr("Play / pause · Space"), tr("Back 10 seconds · ←"), tr("Forward 10 seconds · →"), tr("Volume") + " · ↑ / ↓", tr("Sound · M"), tr("Fullscreen · F") + " / F11", tr("Exit fullscreen · Esc"), tr("Previous video · Ctrl+←"), tr("Next video · Ctrl+→"), tr("Play queue · Ctrl+P"), tr("Save frame · Ctrl+S"), tr("Open library · Ctrl+L"), tr("Close Vivid · Ctrl+Q")]
        QMessageBox.information(self, tr('Keyboard shortcuts'), "\n".join(lines))

    def shortcuts(self):
        self.shortcut_objects = []
        bindings = {"Ctrl+O": self.open_files, "Space": self.toggle_pause, "Left": lambda: self.seek(-10), "Right": lambda: self.seek(10), "Up": lambda: self.volume_slider.setValue(self.volume_slider.value() + 5), "Down": lambda: self.volume_slider.setValue(self.volume_slider.value() - 5), "M": lambda: self.engine.command("cycle", "mute"), "F": self.toggle_fullscreen, "F11": self.toggle_fullscreen, "Escape": self.exit_fullscreen, "Ctrl+Left": lambda: self.next_video(-1), "Ctrl+Right": self.next_video, "Ctrl+P": self.toggle_queue, "Ctrl+S": self.screenshot, "Ctrl+L": self.focus_search, "Ctrl+Q": self.close}
        for key, callback in bindings.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda cb=callback, k=key: self.handle_shortcut(k, cb))
            self.shortcut_objects.append(shortcut)

    def handle_shortcut(self, key, callback):
        if isinstance(QApplication.focusWidget(), QLineEdit) and not key.startswith("Ctrl+") and key not in {"Escape", "F11"}:
            return
        self.note_activity()
        callback()

    def focus_search(self):
        if self.section == "player":
            self.navigate("library")
        self.search.setFocus()
        self.search.selectAll()

    def toggle_fullscreen(self):
        if self.fullscreen:
            self.exit_fullscreen()
            return
        self.enter_fullscreen()

    def enter_fullscreen(self, automatic=False):
        if self.fullscreen:
            return
        self.previous_window_state = self.windowState()
        self.fullscreen_queue_visible = self.queue_panel.isVisible()
        if self.section != "player":
            self.navigate("player")
        self.fullscreen = True
        self.auto_entered_fullscreen = automatic
        self.idle_suppressed = False
        self.header.hide()
        self.sidebar.hide()
        self.footer.hide()
        self.queue_panel.hide()
        self.showFullScreen()
        self.fs_btn.setIcon(icon("collapse", self.colors["muted"]))
        self.set_button_active(self.fs_btn, True)
        self.note_activity()

    def exit_fullscreen(self):
        self.idle_suppressed = True
        self.reveal_player_chrome()
        if self.fullscreen:
            self.fullscreen = False
            self.auto_entered_fullscreen = False
            self.update_workspace_chrome()
            self.queue_panel.setVisible(getattr(self, "fullscreen_queue_visible", False))
            self.showNormal()
            if self.previous_window_state & Qt.WindowState.WindowMaximized:
                self.showMaximized()
            self.fs_btn.setIcon(icon("fullscreen", self.colors["muted"]))
            self.set_button_active(self.fs_btn, False)
        self.note_activity()

    def playback_active(self):
        return self.section == "player" and self.current and self.engine.file_loaded and not self.engine.props.get("pause", True)

    def note_activity(self):
        if not hasattr(self, "idle_timer"):
            return
        self.reveal_player_chrome()
        if self.playback_active():
            self.last_pointer = QCursor.pos()
            self.pointer_timer.start()
            self.idle_timer.start()

    def watch_pointer(self):
        pointer = QCursor.pos()
        if pointer != self.last_pointer:
            self.last_pointer = pointer
            if self.rect().contains(self.mapFromGlobal(pointer)):
                self.note_activity()
            else:
                self.reveal_player_chrome()
                self.idle_timer.stop()

    def hide_player_chrome(self):
        if self.chrome_hidden:
            return
        application = QApplication.instance()
        if not self.playback_active() or not self.isActiveWindow():
            return
        if application.activeModalWidget() or application.activePopupWidget():
            self.idle_timer.start()
            return
        queue_visible = self.queue_panel.isVisible()
        if not self.viewer_only and self.library.settings.get("auto_fullscreen") and not self.fullscreen and not self.idle_suppressed:
            self.enter_fullscreen(automatic=True)
        self.chrome_hidden = True
        self.idle_timer.stop()
        self.queue_was_visible = queue_visible
        self.update_workspace_chrome()
        self.queue_panel.hide()
        self.transition_chrome(0.0)
        self.root.setCursor(Qt.CursorShape.BlankCursor)
        self.surface.setCursor(Qt.CursorShape.BlankCursor)

    def reveal_player_chrome(self):
        if not self.chrome_hidden:
            return
        self.chrome_hidden = False
        self.transition_chrome(1.0)
        if getattr(self, "queue_was_visible", False):
            self.queue_panel.show()
        self.update_workspace_chrome()
        self.root.unsetCursor()
        self.surface.unsetCursor()

    @staticmethod
    def set_button_active(widget, active):
        widget.setProperty("active", bool(active))
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def transition_chrome(self, target):
        self.chrome_animation.stop()
        widgets = (self.player_titlebar, self.controls)
        if self._chrome_progress >= .999 or self._chrome_heights is None:
            self._chrome_heights = [w.height() for w in widgets]
        for widget in widgets:
            if widget.graphicsEffect() is None:
                effect = QGraphicsOpacityEffect(widget)
                effect.setOpacity(self._chrome_progress)
                widget.setGraphicsEffect(effect)
            widget.show()
        self.chrome_animation.setDuration(180)
        self.chrome_animation.setStartValue(self._chrome_progress)
        self.chrome_animation.setEndValue(target)
        self.chrome_animation.start()

    def animate_chrome_frame(self, value):
        self._chrome_progress = float(value)
        for widget, height in zip((self.player_titlebar, self.controls), self._chrome_heights):
            widget.setFixedHeight(max(0, round(height * value)))
            effect = widget.graphicsEffect()
            if effect:
                effect.setOpacity(value)
        margin = round(8 * value)
        self.player_layout.setContentsMargins(margin, margin, margin, margin)
        self.player_layout.setSpacing(round(7 * value))

    def finish_chrome_animation(self):
        for widget in (self.player_titlebar, self.controls):
            if self._chrome_progress < .01:
                widget.hide()
            else:
                widget.setMinimumHeight(0)
                widget.setMaximumHeight(16777215)
                widget.setGraphicsEffect(None)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind in {QEvent.Type.MouseButtonPress, QEvent.Type.Wheel, QEvent.Type.KeyPress}:
            if isinstance(watched, QWidget) and watched.window() == self:
                self.note_activity()
        elif kind == QEvent.Type.MouseButtonDblClick and watched == self.surface:
            self.toggle_fullscreen()
            return True
        return super().eventFilter(watched, event)

    def show_error(self, message):
        bind_text(self.status, 'setText', message.split("\n")[0])
        QMessageBox.warning(self, "Vivid", message)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in SUBTITLE_EXTENSIONS and self.current:
                self.engine.command("sub-add", str(path), "select")
            elif path.is_dir():
                try:
                    files.extend(str(p) for p in path.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
                except OSError:
                    pass
            else:
                files.append(str(path))
        if files:
            self.add_files(files, play=True)
        event.acceptProposedAction()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "resize_timer"):
            self.resize_timer.start()

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self.idle_timer.stop()
        self.pointer_timer.stop()
        self.chrome_animation.stop()
        self.save_position()
        if not self.fullscreen:
            self.geometry_store.setValue(self.geometry_key, self.saveGeometry())
        self.engine.close()
        for job in self.thumb_jobs.values():
            job.cancel()
        self.thumbnails.clear()
        self.thumbnails.waitForDone(1500)
        event.accept()
