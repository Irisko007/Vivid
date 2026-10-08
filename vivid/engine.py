"""Asynchronous mpv IPC. Decoding stays outside the Python/UI process."""

import json
from pathlib import Path
import shutil
import tempfile

from .i18n import tr

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtNetwork import QLocalSocket


class Engine(QObject):
    changed = Signal(str, object)
    loaded = Signal()
    ended = Signal()
    error = Signal(str)
    ready = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._log)
        self.process.errorOccurred.connect(self._process_error)
        self.process.finished.connect(self._finished)
        self.socket = QLocalSocket(self)
        self.socket.connected.connect(self._connected)
        self.socket.readyRead.connect(self._read)
        self.socket.errorOccurred.connect(lambda _: None)
        self.retry = QTimer(self)
        self.retry.setInterval(80)
        self.retry.timeout.connect(self._connect)
        self.clock = QTimer(self)
        self.clock.setInterval(250)
        self.clock.timeout.connect(self._tick)
        self.temp = tempfile.TemporaryDirectory(prefix="vivid-")
        self.socket_path = str(Path(self.temp.name) / "mpv.sock")
        self.pending = []
        self.props = {"pause": True, "time-pos": 0, "duration": 0, "mute": False, "speed": 1}
        self.buffer = b""
        self.last_log = ""
        self.attempts = 0
        self.connected = False
        self.closing = False
        self.started = False
        self.request_id = 0
        self.requests = {}
        self.resume_position = 0
        self.file_loaded = False

    def start(self, window_id, settings):
        if self.started:
            return True
        binary = shutil.which("mpv")
        if not binary:
            self.error.emit(tr('mpv is not installed. Install mpv and restart Vivid.'))
            return False
        self.started = True
        self.attempts = 0
        self.last_log = ""
        self.process.start(binary, [
            "--no-config", "--idle=yes", "--keep-open=yes", "--no-terminal",
            "--osc=no", "--osd-level=0", "--input-default-bindings=no",
            "--input-vo-keyboard=no", "--cursor-autohide=no", "--input-cursor=no", "--input-cursor-passthrough=yes",
            "--vo=gpu", "--gpu-context=x11egl", f"--wid={window_id}",
            f"--input-ipc-server={self.socket_path}",
            f"--hwdec={'auto-safe' if settings.get('hwdec') else 'no'}",
            f"--volume={settings.get('volume', 75)}", "--volume-max=100",
            "--audio-client-name=Vivid", "--sub-auto=fuzzy", "--ytdl=no",
            "--cache=yes", "--demuxer-max-bytes=64MiB", "--demuxer-max-back-bytes=16MiB",
        ])
        self.retry.start()
        return True

    def _connect(self):
        self.attempts += 1
        if self.attempts > 100:
            self.retry.stop()
            self.error.emit((tr('Could not connect to mpv.') + ' ') + self.last_log[-400:])
            self.process.kill()
            return
        if self.socket.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            self.socket.connectToServer(self.socket_path)

    def _connected(self):
        self.retry.stop()
        self.connected = True
        for i, prop in enumerate(["time-pos", "duration", "pause", "volume", "mute", "speed", "track-list", "hwdec-current", "video-params", "eof-reached", "keepaspect", "panscan"]):
            self.command("observe_property", i + 1, prop)
        pending, self.pending = self.pending, []
        for args in pending:
            self.command(*args)
        self.ready.emit()

    def command(self, *args):
        if not self.connected:
            if self.started:
                self.pending.append(args)
            return
        self.request_id += 1
        # Only user commands need error reporting; failed observers are harmless.
        if args[0] not in {"observe_property", "seek", "cycle"}:
            self.requests[self.request_id] = args[0]
        payload = json.dumps({"command": list(args), "request_id": self.request_id}, ensure_ascii=False) + "\n"
        self.socket.write(payload.encode("utf-8"))

    def set(self, name, value):
        self.command("set_property", name, value)

    def load(self, path, position=0):
        self.file_loaded = False
        self.resume_position = max(0, position)
        self.props.update({"time-pos": 0, "duration": 0, "pause": False, "eof-reached": False})
        self.set("pause", True)
        self.command("loadfile", path, "replace")

    def _read(self):
        self.buffer += bytes(self.socket.readAll())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                msg = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            event = msg.get("event")
            if event == "property-change":
                name, value = msg.get("name"), msg.get("data")
                self.props[name] = value
                if name not in {"time-pos"}:
                    self.changed.emit(name, value)
                if name == "pause":
                    if value:
                        self.clock.stop()
                        self._tick()
                    else:
                        self.clock.start()
                elif name == "time-pos" and not self.clock.isActive():
                    self._tick()
                elif name == "eof-reached" and value:
                    self.ended.emit()
            elif event == "file-loaded":
                self.file_loaded = True
                if self.resume_position:
                    self.command("seek", self.resume_position, "absolute+exact")
                self.resume_position = 0
                self.set("pause", False)
                self.loaded.emit()
            elif event == "end-file" and msg.get("reason") == "error":
                self.clock.stop()
                self.error.emit((tr('Could not open video. Check the file and its format.') + ' ') + msg.get("file_error", ""))
            if "request_id" in msg:
                cmd = self.requests.pop(msg["request_id"], None)
                if cmd and msg.get("error") not in (None, "success"):
                    self.error.emit(f"mpv: {cmd}: {msg['error']}")

    def _tick(self):
        self.changed.emit("time-pos", self.props.get("time-pos") or 0)

    def _log(self):
        self.last_log = (self.last_log + bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace"))[-2000:]

    def _process_error(self, error):
        if not self.closing and error == QProcess.ProcessError.FailedToStart:
            self.retry.stop()
            self.started = False
            self.pending.clear()
            self.error.emit((tr('Could not start mpv:') + ' ') + self.process.errorString())

    def _finished(self, code, status):
        self.file_loaded = False
        self.retry.stop()
        self.clock.stop()
        self.socket.abort()
        self.connected = self.started = False
        self.pending.clear()
        self.requests.clear()
        self.buffer = b""
        if not self.closing:
            self.error.emit((tr('mpv stopped. Open the file again.') + ' ') + self.last_log[-500:])

    def close(self):
        self.closing = True
        self.retry.stop()
        self.clock.stop()
        if self.connected:
            self.command("quit")
            self.socket.flush()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            if not self.process.waitForFinished(1200):
                self.process.kill()
                self.process.waitForFinished(1000)
        self.socket.abort()
        self.temp.cleanup()
