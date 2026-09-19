#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ARTIFACT="${RELEASE_ARTIFACT:-}"
if [[ -z "$ARTIFACT" ]]; then
  ARTIFACT="$(find . -maxdepth 1 -type f -name 'remnawave_vpn_shop_*.zip' -printf '%f\n' | sort -V | tail -1)"
fi
[[ -n "$ARTIFACT" && -f "$ARTIFACT" ]] || { echo "Релизный ZIP не найден" >&2; exit 2; }
DEFAULT_MANIFEST="${ARTIFACT%.zip}_manifest.json"
MANIFEST="${1:-$DEFAULT_MANIFEST}"
SIG="${2:-${ARTIFACT%.zip}_manifest.sig}"
PUBKEY="${RELEASE_PUBLIC_KEY_FILE:-release-public-key.pem}"
[[ -f "$MANIFEST" && -f "$SIG" && -f "$PUBKEY" ]] || { echo "Требуются manifest, подпись и публичный ключ" >&2; exit 2; }
openssl dgst -sha256 -verify "$PUBKEY" -signature "$SIG" "$MANIFEST"
python3 - "$MANIFEST" "$ARTIFACT" <<'PY'
import json,sys
manifest_path, artifact = sys.argv[1], sys.argv[2]
with open(manifest_path, encoding="utf-8") as fh:
    m=json.load(fh)
if m.get("artifact") != artifact:
    raise SystemExit(f"Manifest artifact mismatch: {m.get('artifact')} != {artifact}")
sha=m.get("sha256")
if not sha or len(sha) != 64:
    raise SystemExit("Manifest has no valid SHA-256")
PY
python3 - "$MANIFEST" "$ARTIFACT" <<'PY'
import hashlib, json, sys
manifest_path, artifact = sys.argv[1], sys.argv[2]
with open(manifest_path, encoding="utf-8") as fh:
    expected=json.load(fh)["sha256"]
h=hashlib.sha256()
with open(artifact,"rb") as fh:
    for chunk in iter(lambda: fh.read(1024*1024), b""):
        h.update(chunk)
actual=h.hexdigest()
if actual != expected:
    raise SystemExit(f"SHA-256 mismatch: {actual} != {expected}")
print(f"SHA-256 OK: {actual}")
PY
unzip -tq "$ARTIFACT" >/dev/null
echo "Release verification OK: $ARTIFACT"
