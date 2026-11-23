#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM

install -d "$STAGE/DEBIAN" "$STAGE/usr/lib/virtcore" "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/scalable/apps"
install -m 0644 "$ROOT/packaging/debian/control" "$STAGE/DEBIAN/control"
install -m 0644 "$ROOT/app.py" "$STAGE/usr/lib/virtcore/"
install -m 0755 "$ROOT/packaging/virtcore" "$STAGE/usr/bin/virtcore"
install -m 0644 "$ROOT/packaging/debian/virtcore.desktop" "$STAGE/usr/share/applications/virtcore.desktop"
install -m 0644 "$ROOT/packaging/virtcore.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/virtcore.svg"

mkdir -p "$ROOT/dist"
dpkg-deb --root-owner-group --build "$STAGE" "$ROOT/dist/virtcore_1.0.0~beta2_all.deb"
printf 'Built %s\n' "$ROOT/dist/virtcore_1.0.0~beta2_all.deb"
