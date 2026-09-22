#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# This file also serves as the GitHub-raw bootstrap.
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ! -f "$ROOT/lib/common.sh" ]]; then
  : "${INSTALLER_REPO:?Set INSTALLER_REPO=USER/REPO for raw bootstrap}"
  INSTALLER_REF=${INSTALLER_REF:-main}
  [[ $INSTALLER_REPO =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $INSTALLER_REF =~ ^[A-Za-z0-9_.-]+$ ]] || exit 2
  bootstrap=$(mktemp -d)
  trap 'rm -rf -- "$bootstrap"' EXIT
  command -v curl >/dev/null || { echo 'Install curl first'; exit 1; }
  curl -fLsS --retry 3 "https://api.github.com/repos/$INSTALLER_REPO/commits/$INSTALLER_REF" -o "$bootstrap/ref.json"
  # Ubuntu ships python3; only a commit SHA is accepted from this response.
  commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$bootstrap/ref.json")
  [[ $commit =~ ^[a-f0-9]{40}$ ]] || exit 2
  curl -fLsS --retry 3 "https://codeload.github.com/$INSTALLER_REPO/tar.gz/$commit" -o "$bootstrap/repo.tgz"
  mkdir "$bootstrap/src"
  tar -xzf "$bootstrap/repo.tgz" -C "$bootstrap/src" --strip-components=1
  bash "$bootstrap/src/install.sh" "$@"
  exit
fi
if [[ ${1:-} == --update-only ]]; then
  [[ $# == 1 ]] || { echo '--update-only takes no additional options'; exit 2; }
  exec bash "$ROOT/update.sh"
fi
# shellcheck source=lib/common.sh
source "$ROOT/lib/common.sh"
for module in 3xui certs subscription inbounds nginx firewall; do source "$ROOT/lib/$module.sh"; done
PANEL_VERSION=latest
CONFIG=''
while (($#)); do
  case $1 in
    --version) PANEL_VERSION=${2:?Missing version}; shift 2 ;;
    --config) CONFIG=${2:?Missing config}; shift 2 ;;
    --help) echo 'install.sh [--version latest|3.8.5] [--config /root/config.env] | --update-only'; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done
[[ $EUID == 0 ]] || die 'Run as root'
if [[ -n $CONFIG ]]; then
  [[ -f $CONFIG && $(stat -c %u "$CONFIG") == 0 ]] || die 'Config must be a root-owned file'
  # Trusted shell configuration, never fetched from a subscription or database.
  source "$CONFIG"
fi
export PANEL_VERSION AUTO_DOMAIN_SUFFIX=${AUTO_DOMAIN_SUFFIX:-cdn-one.org} PUBLIC_IPV4=${PUBLIC_IPV4:-}
export ACME_EMAIL=${ACME_EMAIL:-} ACME_STAGING=${ACME_STAGING:-no}
source /etc/os-release
[[ $ID == ubuntu && ( $VERSION_ID == 22.04 || $VERSION_ID == 24.04 ) ]] || die 'Supported target: Ubuntu 22.04/24.04'
mkdir -p "$STATE" /var/log/single443
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Another installer/refresh is running'
exec > >(tee -a /var/log/single443/install.log) 2>&1
log 'Preparing dependencies'
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q curl ca-certificates python3 openssl nginx libnginx-mod-stream certbot dnsutils iproute2 util-linux nftables
preflight
firewall_preflight
resolve_release
init_state
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
backup_begin
configure_firewall
nft -s list table inet single443 > /etc/single443/firewall-expected.txt
install_acme_web
obtain_cert
install_panel
configure_panel
configure_inbounds
subscription_discover
validate_xray
render_nginx
activate_nginx
if ! bash "$ROOT/diagnose.sh"; then die 'Post-install verification failed'; fi
# Keep the installed entry points available for reruns and renewal.
mkdir -p /opt/single443
if [[ $(realpath "$ROOT") != /opt/single443 ]]; then cp -a "$ROOT/." /opt/single443/; fi
install_renew_hook
TX_ACTIVE=no
trap - ERR INT TERM
log "Completed. Credentials and subscription URLs: $STATE/access.txt (root only)"
log "Backup: $BACKUP"
