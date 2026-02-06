#!/bin/bash

wget https://github.com/bluenviron/mediamtx/releases/download/v1.16.0/mediamtx_v1.16.0_linux_arm64.tar.gz
tar -xzf mediamtx_v1.16.0_linux_arm64.tar.gz

# Füge Kamera-Konfiguration nach dem paths: Abschnitt ein
sed -i '/^paths:/a\  cam:\n    source: rpiCamera\n    rpiCameraWidth: 1280\n    rpiCameraHeight: 720\n    rpiCameraFPS: 30' mediamtx.yml

echo "MediaMTX erfolgreich initialisiert und Kamera-Konfiguration hinzugefügt!"