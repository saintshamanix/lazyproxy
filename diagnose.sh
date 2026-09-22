#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
source "$ROOT/lib/common.sh"
source "$ROOT/lib/firewall.sh"
firewall_verify
python3 "$ROOT/lib/engine.py" diagnose
