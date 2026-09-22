#!/usr/bin/env bash
set -Eeuo pipefail
resolve_release() {
  case $(uname -m) in x86_64) ARCH=amd64 ;; aarch64) ARCH=arm64 ;; *) die 'Only amd64/arm64 supported';; esac
  if [[ $PANEL_VERSION == latest ]]; then
    curl -fLsS --retry 3 https://api.github.com/repos/MHSanaei/3x-ui/releases/latest -o "$STATE/release.json"
  else
    PANEL_VERSION=v${PANEL_VERSION#v}
    [[ $PANEL_VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die 'Invalid release version'
    curl -fLsS --retry 3 "https://api.github.com/repos/MHSanaei/3x-ui/releases/tags/$PANEL_VERSION" -o "$STATE/release.json"
  fi
  TAG=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag_name"])' "$STATE/release.json")
  [[ $TAG == v3.8.5 ]] || die "Six-inbound AmneziaWG adapter verified for v3.8.5; pin --version 3.8.5 (requested $TAG)"
  export TAG ARCH
  log "Resolved upstream release $TAG ($ARCH)"
}
install_panel() {
  local installed
  installed=$(helper value installed_version)
  if [[ $installed != "$TAG" || ! -x /usr/local/x-ui/x-ui ]]; then
    mkdir -p "$BACKUP/download" "$BACKUP/unpack"
    local asset=x-ui-linux-$ARCH.tar.gz
    curl -fLsS --retry 3 "https://github.com/MHSanaei/3x-ui/releases/download/$TAG/$asset" -o "$BACKUP/download/$asset"
    helper verify-release "$BACKUP/download/$asset" "$STATE/release.json"
    tar -xzf "$BACKUP/download/$asset" -C "$BACKUP/unpack"
    [[ -x $BACKUP/unpack/x-ui/x-ui ]] || die 'Unexpected release archive'
    rm -rf /usr/local/x-ui
    cp -a "$BACKUP/unpack/x-ui" /usr/local/x-ui
  fi
  # Defaults are from the selected tag, not guessed SQLite column positions.
  curl -fLsS --retry 3 "https://raw.githubusercontent.com/MHSanaei/3x-ui/$TAG/internal/web/service/setting.go" -o "$STATE/upstream-setting.go"
  curl -fLsS --retry 3 "https://raw.githubusercontent.com/MHSanaei/3x-ui/$TAG/x-ui.service.debian" -o /etc/systemd/system/x-ui.service
  mkdir -p /etc/x-ui
  /usr/local/x-ui/x-ui migrate
  if [[ $(helper value configured) != True ]]; then
    helper bootstrap-cli
  fi
  systemctl daemon-reload
  systemctl enable x-ui
  systemctl start x-ui
  helper wait-panel
}
configure_panel() { helper configure-panel; }
validate_xray() {
  local binary
  binary=$(find /usr/local/x-ui/bin -maxdepth 1 -type f -name 'xray-linux-*' -perm /111 -print -quit)
  [[ -n $binary && -f /usr/local/x-ui/bin/config.json ]] || die 'Xray binary/config missing'
  (cd /usr/local/x-ui && XRAY_LOCATION_ASSET=/usr/local/x-ui/bin "$binary" run -test -config /usr/local/x-ui/bin/config.json)
}
