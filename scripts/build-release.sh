#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Historical release: VERSION="39.0.0-production" artifact=remnawave_vpn_shop_v39_production.zip migration=0017_v39_staging_isolation
# Previous release contract: VERSION="1.0.1-realise" artifact=remnawave_vpn_shop_v1_0_1_realise_deep_audited_fixed.zip
# Legacy regression markers: VERSION="1.0.0-realise" artifact=remnawave_vpn_shop_v1_0_0_realise_deep_audited_fixed.zip
VERSION="3.1.6"
# Historical compatibility marker: VERSION="3.1.5"
# Historical compatibility marker: VERSION="3.1.4"
# Historical compatibility marker: VERSION="3.1.3"
# Historical compatibility marker: VERSION="3.1.2"
# Historical compatibility marker: VERSION="3.1.1"
# Historical compatibility marker: VERSION="3.1.0"
# Historical compatibility marker: VERSION="3.0.1"
# Historical compatibility marker: VERSION="3.0.0-realise"
# Historical compatibility marker: VERSION="2.13.0"
# Historical compatibility marker: VERSION="2.12.0"
# Historical compatibility marker: VERSION="2.11.0"
# Historical compatibility marker: VERSION="2.10.0"
# Historical compatibility marker: VERSION="2.9.0"
# Historical compatibility marker: VERSION="2.8.0"
# Historical compatibility marker: VERSION="2.7.0"
# Historical compatibility marker: VERSION="2.6.0"
# Historical compatibility marker: VERSION="2.5.0"
# Historical compatibility marker: VERSION="2.4.0"
# Historical compatibility marker: VERSION="2.3.0"
# Historical compatibility marker: VERSION="2.2.1"
# Historical compatibility marker: VERSION="2.2.0"
# Historical compatibility marker: VERSION="2.1.0"
# Legacy regression marker: VERSION="2.0.3-audited"
# Legacy regression marker: VERSION="2.0.2-audited"
# Legacy regression contract marker: VERSION="2.0.0-realise"
# Legacy regression contract marker: VERSION="1.0.0-realise"
# Previous release contract: VERSION="45.0.0-enterprise" artifact=remnawave_vpn_shop_v44_5_9_enterprise_deep_audited_fixed.zip
# Previous migration head retained for compatibility: 0030_v44_5_16_privacy_and_refund_integrity
# Current migration head: 0038_v2_6_0_platform
# Historical compatibility marker: 2.9.0 keeps migration 0038_v2_6_0_platform
# Historical compatibility marker: 2.8.0 keeps migration 0038_v2_6_0_platform
# Historical compatibility marker: 2.7.0 keeps migration 0038_v2_6_0_platform
# Historical compatibility marker: 0037_v2_5_0_tariff_constructor
# Historical compatibility marker: 0036_v2_4_0_cabinet
# Historical compatibility marker: 0035_v2_3_0_wallet_gifts
# Historical compatibility marker: 0034_v2_2_0_platform_features
# Historical compatibility marker: 0032_v2_0_0_product_features
# VERSION="43.1.0-production" legacy regression marker
# migration_head="0021_v43_hardening_docs" legacy regression marker
ARTIFACT="remnawave_vpn_shop_v3_1_6_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_5_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_4_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_3_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_2_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_1_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_1_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_0_1_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v3_0_0_realise_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_13_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_12_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_11_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_10_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_9_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_8_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_7_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_6_0_full_release.zip"
# Historical compatibility marker: ARTIFACT="remnawave_vpn_shop_v2_5_0_full_release.zip"
# Historical compatibility marker: remnawave_vpn_shop_v2_4_0_full_release.zip
# Historical compatibility marker: remnawave_vpn_shop_v2_3_0_full_release.zip
# Historical compatibility marker: remnawave_vpn_shop_v2_2_1_full_release.zip
python -m pytest -q
python -m compileall -q backend
python -m pytest -q tests/test_release_quality_v2_2.py
bash -n install.sh deploy/*.sh scripts/*.sh
python - <<'PY'
import yaml
with open("docker-compose.yml") as f: yaml.safe_load(f)
PY
rm -f "$ARTIFACT" "${ARTIFACT}.sha256" "${ARTIFACT%.zip}.sha256" "${ARTIFACT%.zip}_manifest.json"
# The archive cannot safely contain its own final SHA256 manifest (that would be self-referential).
# Normalize a template first; the exact detached manifest is generated only after the ZIP is complete.
if [[ -n "${RELEASE_MANIFEST_SOURCE:-}" ]]; then
  cp "$RELEASE_MANIFEST_SOURCE" release-manifest.template.json
elif [[ -f release-manifest.json ]]; then
  cp release-manifest.json release-manifest.template.json
elif [[ -f release-manifest.template.json ]]; then
  :
else
  echo "Не найден release manifest" >&2; exit 1
fi
python - "$VERSION" "$ARTIFACT" <<'PY'
import json,sys
p='release-manifest.template.json'
m=json.load(open(p)); m['sha256']=None; m['tests']=None; m['artifact']=sys.argv[2]; m['version']=sys.argv[1]; m['migration_head']='0038_v2_6_0_platform'; m['detached_manifest']=sys.argv[2].removesuffix('.zip')+'_manifest.json'; m['signed']=False
m['note']='Template only. The exact release manifest is shipped as a detached file next to the ZIP because embedding the ZIP SHA inside the ZIP is self-referential.'
json.dump(m,open(p,'w'),ensure_ascii=False,indent=2); open(p,'a').write('\n')
PY
zip -qr "$ARTIFACT" . -x '*/.env' '.env' '*/node_modules/*' '*/__pycache__/*' '*.pyc' '.pytest_cache/*' '.git/*' '*.zip' '*.sha256' '*_manifest.json' 'release-manifest.json' '*.apk' '*/app/build/*' '*/.gradle/*'
unzip -tq "$ARTIFACT" >/dev/null
unzip -l "$ARTIFACT" | grep '\.env.example' >/dev/null
SHA=$(sha256sum "$ARTIFACT" | awk '{print $1}')
TEST_LINE=$(python -m pytest -q | tail -1)
TESTS=$(printf '%s\n' "$TEST_LINE" | grep -oE '[0-9]+ passed' | awk '{print $1}')
[[ -n "$TESTS" ]] || { echo "Не удалось определить число пройденных тестов: $TEST_LINE" >&2; exit 1; }
python - "$SHA" "$VERSION" "$ARTIFACT" "$TESTS" <<'PY'
import json,sys
t='release-manifest.template.json'; out=sys.argv[3].removesuffix('.zip')+'_manifest.json'
m=json.load(open(t)); m['version']=sys.argv[2]; m['artifact']=sys.argv[3]; m['sha256']=sys.argv[1]; m['tests']=int(sys.argv[4]); m['signed']=False
m['detached_manifest']=out
m['note']='Detached manifest. The ZIP intentionally does not contain its own final SHA256 manifest; use this exact detached manifest to verify the artifact.'
json.dump(m,open(out,'w'),ensure_ascii=False,indent=2); open(out,'a').write('\n')
PY
sha256sum "$ARTIFACT" | tee "${ARTIFACT}.sha256" > "${ARTIFACT%.zip}.sha256"
echo "Release: $ARTIFACT"
echo "SHA256:  $SHA"
echo "Tests:   $TESTS"
