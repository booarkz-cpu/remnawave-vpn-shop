# Release notes 3.1.3

## Русский

Установщик **3.1.3** снова задаёт вопросы, когда его запускают командой `curl | bash`. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android — **2.12.0**. Исправления **3.1.2** остаются. Production gate по-прежнему требует строку `FULL_E2E_PASS`.

### Критическая ошибка

В **3.1.2** команда

```bash
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

печатала приветствие и сразу завершалась строкой `ERROR: installation failed at line 34`. Канал `curl` занят текстом скрипта, поэтому `read` получал конец файла и `set -e` останавливал установку до первого вопроса.

С **3.1.3** `install.sh` подключает `/dev/tty` перед запуском `deploy/install-vps.sh`. Функция `prompt` тоже читает ответ с терминала, если stdin не терминал. Скрытые поля по-прежнему используют `read -s`. Если терминала нет, скрипт пишет «Нет терминала для вопросов установщика» и просит `INSTALL_NONINTERACTIVE=1`.

### Что не менялось

- Вопросы и порядок из `INSTALL_STEPS.md` те же, что в **3.1.2**.
- Кнопка **Разрешить реальные платежи** по-прежнему ждёт `FULL_E2E_PASS`. Порядок — раздел 9.15 `INSTRUCTION.md`.
- Лицензия — Remnawave VPN Shop Proprietary License 1.0.

## English

Installer **3.1.3** asks questions again when it is started with `curl | bash`. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The **3.1.2** fixes remain. The production gate still requires the line `FULL_E2E_PASS`.

### Critical bug

In **3.1.2** the command

```bash
curl -fsSL https://raw.githubusercontent.com/booarkz-cpu/remnawave-vpn-shop/main/install.sh | sudo bash
```

printed the greeting and then stopped with `ERROR: installation failed at line 34`. The `curl` pipe is occupied by the script text, so `read` hit end of file and `set -e` stopped the install before the first question.

From **3.1.3**, `install.sh` attaches `/dev/tty` before it starts `deploy/install-vps.sh`. `prompt` also reads the answer from the terminal when stdin is not a terminal. Hidden fields still use `read -s`. If there is no terminal, the script prints «Нет терминала для вопросов установщика» and asks for `INSTALL_NONINTERACTIVE=1`.

### Unchanged

- The questions and their order in `INSTALL_STEPS.md` are the same as in **3.1.2**.
- **Разрешить реальные платежи** (Allow live payments) still waits for `FULL_E2E_PASS`. The order is section 9.15 of `INSTRUCTION.md`.
- The license remains Remnawave VPN Shop Proprietary License 1.0.
