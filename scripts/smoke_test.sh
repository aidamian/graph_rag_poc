#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "Checking API health..."
curl -sf "${API_BASE_URL}/health"
echo

echo "Checking graph summary..."
curl -sf "${API_BASE_URL}/summary" >/dev/null
echo "summary ok"

echo "Running investigation query..."
response="$(
  curl -sf \
    -X POST "${API_BASE_URL}/ask" \
    -H 'Content-Type: application/json' \
    -d '{"question":"How are the VPN exploit alerts connected to the ransomware on fs-02?","mode":"compare","top_k":8}'
)"

python3 - <<'PY' "$response"
import json
import sys

payload = json.loads(sys.argv[1])
print("question:", payload["question"])
print("graph provider:", payload["graph"]["answer"]["provider"])
print("graph answer:", payload["graph"]["answer"]["answer"])
print("comparison:", payload["comparison"])
PY

