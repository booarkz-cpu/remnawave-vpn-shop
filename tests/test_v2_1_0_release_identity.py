from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_matches_audited_release_contract():
    main = (ROOT / "backend/app/main.py").read_text()
    build = (ROOT / "scripts/build-release.sh").read_text()
    manifest = (ROOT / "release-manifest.template.json").read_text()
    assert 'APP_VERSION = "2.1.0"' in main
    assert 'VERSION="2.1.0"' in build
    assert '"version": "2.1.0"' in manifest
