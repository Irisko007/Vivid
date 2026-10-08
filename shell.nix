{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (p: [ p.pyside6 p.pillow ]))
    pkgs.mpv pkgs.ffmpeg pkgs.qt6.qtbase
  ];
  QT_QPA_PLATFORM = "xcb";
  VIVID_TRANSLATIONS_DIR = "${pkgs.qt6.qttranslations}/translations";
}
