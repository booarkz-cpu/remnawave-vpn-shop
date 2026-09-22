#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STRICT_SECURITY="${STRICT_SECURITY:-0}"
echo "== Python syntax =="
python3 -m compileall -q backend
if command -v pip-audit >/dev/null 2>&1; then
  echo "== pip-audit =="; pip-audit -r backend/requirements.txt
else
  if [[ "$STRICT_SECURITY" == "1" ]]; then echo "FAIL: pip-audit is required in strict security mode" >&2; exit 2; fi
  echo "WARN: pip-audit not installed; install it in CI to run dependency vulnerability scanning."
fi
for dir in admin miniapp cabinet; do
  if [[ -f "$dir/package-lock.json" ]] && command -v npm >/dev/null 2>&1; then
    echo "== npm audit $dir =="; (cd "$dir" && npm audit --omit=dev --audit-level=high)
  else
    if [[ "$STRICT_SECURITY" == "1" ]]; then echo "FAIL: $dir frontend dependency audit prerequisites are missing" >&2; exit 2; fi
    echo "WARN: $dir/package-lock.json missing or npm unavailable; frontend dependency audit skipped."
  fi
done
if command -v docker >/dev/null 2>&1; then
  docker compose config >/dev/null
  echo "Docker Compose config: OK"
else
  if [[ "$STRICT_SECURITY" == "1" ]]; then echo "FAIL: Docker is required in strict security mode" >&2; exit 2; fi
  echo "WARN: Docker daemon unavailable; container scan skipped."
fi

if command -v trivy >/dev/null 2>&1; then
  echo "== Trivy filesystem scan =="
  trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 1 .
else
  if [[ "$STRICT_SECURITY" == "1" ]]; then echo "FAIL: trivy is required in strict security mode" >&2; exit 2; fi
  echo "WARN: trivy unavailable; install it in CI for filesystem/container vulnerability scanning."
fi
if command -v syft >/dev/null 2>&1; then
  mkdir -p security-artifacts
  syft dir:. -o cyclonedx-json > security-artifacts/sbom.cdx.json
  echo "SBOM written to security-artifacts/sbom.cdx.json"
else
  if [[ "$STRICT_SECURITY" == "1" ]]; then echo "FAIL: syft is required in strict security mode" >&2; exit 2; fi
  echo "WARN: syft unavailable; install it in CI to generate an SBOM."
fi
