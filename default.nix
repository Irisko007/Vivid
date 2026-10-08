{ pkgs ? import <nixpkgs> {} }:
let
  python = pkgs.python3.withPackages (p: [ p.pyside6 ]);
in pkgs.stdenvNoCC.mkDerivation {
  pname = "vivid-player";
  version = "1.3.0";
  src = builtins.path {
    path = ./vivid;
    name = "vivid-source";
    filter = path: type: builtins.baseNameOf path != "__pycache__";
  };
  nativeBuildInputs = [ pkgs.makeWrapper ];
  dontBuild = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/vivid/vivid" "$out/bin" "$out/share/applications" "$out/share/icons/hicolor/512x512/apps"
    cp -r . "$out/share/vivid/vivid/"
    cp assets/vivid.png "$out/share/icons/hicolor/512x512/apps/io.vivid.Player.png"
    mkdir -p "$out/share/licenses/vivid"
    cp ${./LICENSE} "$out/share/licenses/vivid/LICENSE"
    cp assets/fonts/OFL.txt "$out/share/licenses/vivid/OFL.txt"
    makeWrapper ${python}/bin/python3 "$out/bin/vivid" \
      --add-flags "-m vivid" \
      --prefix PYTHONPATH : "$out/share/vivid" \
      --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.mpv pkgs.ffmpeg ]} \
      --set QT_PLUGIN_PATH "${pkgs.qt6.qtbase}/${pkgs.qt6.qtbase.qtPluginPrefix}" \
      --set VIVID_TRANSLATIONS_DIR "${pkgs.qt6.qttranslations}/translations"
    cat > "$out/share/applications/io.vivid.Player.desktop" <<EOF
    [Desktop Entry]
    Type=Application
    Name=Vivid
    GenericName=Video Player
    GenericName[ru]=Видеоплеер
    Exec=$out/bin/vivid %F
    Icon=io.vivid.Player
    Terminal=false
    Categories=AudioVideo;Video;Player;
    MimeType=video/3gpp;video/3gpp2;video/annodex;video/dv;video/isivideo;video/mj2;video/mp2t;video/mp4;video/mpeg;video/ogg;video/quicktime;video/vnd.avi;video/vnd.mpegurl;video/vnd.radgamettools.bink;video/vnd.radgamettools.smacker;video/vnd.rn-realvideo;video/vnd.vivo;video/vnd.youtube.yt;video/wavelet;video/webm;video/x-anim;video/x-flic;video/x-flv;video/x-javafx;video/x-matroska;video/x-matroska-3d;video/x-mjpeg;video/x-mng;video/x-ms-wmp;video/x-ms-wmv;video/x-nsv;video/x-ogm+ogg;video/x-sgi-movie;video/x-theora+ogg;video/x-msvideo;video/x-m4v;video/x-ms-asf;
    StartupWMClass=vivid
    EOF
    runHook postInstall
  '';
  meta = {
    description = "Native Linux video player with a Fluent inspired interface";
    license = pkgs.lib.licenses.mit;
    platforms = pkgs.lib.platforms.linux;
    mainProgram = "vivid";
  };
}
