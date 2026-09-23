"""3.1.3 installer reads answers from the terminal when stdin is a pipe."""
import os
import pty
import select
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_313_is_first():
    main = (ROOT / "backend/app/main.py").read_text()
    assert main.index('APP_VERSION = "3.1.3"') < main.index('APP_VERSION = "3.1.2"')
    assert main.index('APP_VERSION = "3.1.2"') < main.index('APP_VERSION = "3.1.1"')
    build = (ROOT / "scripts/build-release.sh").read_text()
    assert build.index('VERSION="3.1.3"') < build.index('VERSION="3.1.2"')
    assert build.index('ARTIFACT="remnawave_vpn_shop_v3_1_3_full_release.zip"') < build.index("remnawave_vpn_shop_v3_1_2_full_release.zip")
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert installer.index('INSTALLER_VERSION="3.1.3"') < installer.index('INSTALLER_VERSION="3.1.2"')
    assert installer.index('INSTALLER_VERSION="3.1.2"') < installer.index('INSTALLER_VERSION="3.1.1"')


def test_piped_install_reads_the_terminal():
    wrapper = (ROOT / "install.sh").read_text()
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    assert "exec bash" in wrapper
    assert 'exec bash "$SOURCE_DIR/deploy/install-vps.sh" </dev/tty' in wrapper
    assert "INSTALL_NONINTERACTIVE" in wrapper
    assert "Нет терминала для вопросов установщика" in wrapper
    prompt = installer[installer.index("prompt() {"): installer.index("prompt_required() {")]
    assert "tty=/dev/tty" in prompt
    assert 'read -r -p "$label${default:+ [$default]}: " value <"$tty"' in prompt
    assert 'read -r -s -p "$label: " value <"$tty"' in prompt
    assert "Нет терминала для вопросов установщика" in prompt


def test_prompt_answers_from_a_pty_when_stdin_is_a_pipe():
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    prompt = installer[installer.index("prompt() {"): installer.index("prompt_required() {")]
    script = (
        "set -Eeuo pipefail\n"
        "die(){ printf '%s\\n' \"$*\" >&2; exit 1; }\n"
        + prompt
        + "\nprompt BASE_DOMAIN \"Основной домен\" \"\"\n"
        + "printf 'ANSWER:%s\\n' \"$BASE_DOMAIN\"\n"
    )
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["bash", "-s"],
        stdin=subprocess.PIPE,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        start_new_session=True,
        preexec_fn=_claim_tty,
    )
    os.close(slave)
    assert proc.stdin is not None
    proc.stdin.write(script.encode())
    proc.stdin.close()
    os.write(master, b"vpn.example.com\n")
    chunks = []
    while proc.poll() is None or select.select([master], [], [], 0)[0]:
        ready, _, _ = select.select([master], [], [], 5)
        if not ready:
            break
        try:
            chunks.append(os.read(master, 4096))
        except OSError:
            break
        if b"ANSWER:" in b"".join(chunks):
            break
    proc.wait(timeout=5)
    os.close(master)
    text = b"".join(chunks).decode(errors="replace")
    assert proc.returncode == 0, text
    assert "ANSWER:vpn.example.com" in text
    assert "installation failed at line" not in text


def test_noninteractive_prompt_does_not_read_stdin():
    installer = (ROOT / "deploy/install-vps.sh").read_text()
    prompt = installer[installer.index("prompt() {"): installer.index("prompt_required() {")]
    script = "set -Eeuo pipefail\n" + prompt + "\nprompt BASE_DOMAIN \"Основной домен\" \"fallback.example\"\nprintf '%s\\n' \"$BASE_DOMAIN\"\n"
    proc = subprocess.run(
        ["bash", "-s"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "INSTALL_NONINTERACTIVE": "1", "BASE_DOMAIN": "shop.example.com"},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "shop.example.com"


def test_docs_describe_313_and_keep_312():
    readme = (ROOT / "README.md").read_text()
    instruction = (ROOT / "INSTRUCTION.md").read_text()
    notes = (ROOT / "RELEASE_NOTES_V3_1_3.md").read_text()
    steps = (ROOT / "INSTALL_STEPS.md").read_text()
    docs = (ROOT / "DOCUMENTATION.md").read_text()
    ui = (ROOT / "admin/src/main.tsx").read_text()
    assert "3.1.3" in readme and "3.1.2" in readme and "3.1.1" in readme
    assert "личный кабинет" in readme and "Конструктор тарифов" in readme
    assert "installation failed at line 34" in readme
    assert instruction.count("## 9.17.") == 2
    assert instruction.count("## 9.16.") == 2
    assert "FULL_E2E_PASS" in instruction
    assert "Русский" in notes and "English" in notes
    assert "2.10.0" in notes and "2.12.0" in notes and "0038_v2_6_0_platform" in notes
    assert '"version": "3.1.2"' in steps
    assert '"version": "3.1.3"' in steps
    assert "RELEASE_NOTES_V3_1_3.md" in docs and "RELEASE_NOTES_V3_1_2.md" in docs
    assert "client-logo" not in ui


def _claim_tty():
    import fcntl
    import termios

    fcntl.ioctl(1, termios.TIOCSCTTY, 0)
