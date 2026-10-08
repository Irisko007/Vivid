import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Vivid — native Linux video player")
    parser.add_argument("files", nargs="*", help="Video files to open")
    parser.add_argument("--viewer", action="store_true", help="Open the windowed viewer only")
    parser.add_argument("--version", action="version", version="Vivid 1.3.0")
    args = parser.parse_args()
    # mpv --wid embeds into an X11 parent. On Wayland use the XWayland bridge.
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("Install dependencies: python3 -m pip install .\nOn NixOS: nix-shell --run './run.sh'", file=sys.stderr)
        return 1
    if not os.environ.get("DISPLAY"):
        print("Vivid requires an X11 session or Wayland with XWayland (DISPLAY).", file=sys.stderr)
        return 1
    from .window import Window
    application = QApplication(["vivid"])
    application.setApplicationName("Vivid")
    application.setOrganizationName("Vivid")
    application.setDesktopFileName("io.vivid.Player")
    application.setStyle("Fusion")
    window = Window(viewer_only=args.viewer or bool(args.files))
    window.show()
    if args.files:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: window.add_files(args.files, play=True))
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
