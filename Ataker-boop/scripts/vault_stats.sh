#!/usr/bin/env bash
# Vault stats (no LLM). Usage:
#   source /Volumes/AtakerDirty/Ataker/env.fortress.sh
#   bash Ataker-boop/scripts/vault_stats.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${ROOT}/Ataker-boop/.venv/bin/python"
VAULT="${ATAKER_VAULT:-/Volumes/AtakerDirty/Ataker/ataker_vault/attacks.db}"
export PYTHONPATH="${ROOT}/Ataker-boop${PYTHONPATH:+:$PYTHONPATH}"
exec "$PY" - <<PY
from ataker.vault import AttackVault
import json, os
v = AttackVault(os.environ.get("ATAKER_VAULT", "${VAULT}"))
print(json.dumps(v.get_stats(), ensure_ascii=False, indent=2))
PY
