#!/usr/bin/env bash
# Совместимость: качает только Planner (Dolphin). Полная готовка — download_ataker_models_air.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/download_ataker_models_air.sh" --planner "$@"
