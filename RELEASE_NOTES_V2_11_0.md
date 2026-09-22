# Remnawave VPN Shop 2.11.0

Схема базы остаётся `0038_v2_6_0_platform`. Лицензия остаётся Remnawave VPN Shop Proprietary License 1.0 (`LicenseRef-Proprietary`). Новых APK в этом релизе нет: пакеты покупателя и администратора остаются release-сборками **2.10.0**. IPA по-прежнему собирается в Xcode.

The database schema stays `0038_v2_6_0_platform`. The license stays the Remnawave VPN Shop Proprietary License 1.0. This release does not attach new APKs. The buyer and administrator packages remain the **2.10.0** release builds. The IPA is still produced in Xcode.

## Документы / Documents

`README.md` на GitHub написан двумя полными частями: русский и English. То же покрытие у `INSTRUCTION.md`, `INSTALL.md`, `MODULES.md`, `SECURITY.md`, `MOBILE.md` и `FUNCTIONS.md`.

The GitHub `README.md` has a full Russian part and a full English part. `INSTRUCTION.md`, `INSTALL.md`, `MODULES.md`, `SECURITY.md`, `MOBILE.md` and `FUNCTIONS.md` keep both languages.

## Обновление с GitHub / GitHub update

`sudo bash /opt/vpn-shop/scripts/update-from-github.sh`

1. Скрипт читает последний релиз `booarkz-cpu/remnawave-vpn-shop`.
2. Скачивает zip `full_release` и соседний `.sha256`. Редирект на другой хост отклоняется. Разрешены `github.com`, `release-assets.githubusercontent.com` и `objects.githubusercontent.com`.
3. Сверяет SHA-256. Отклоняет symlink, путь с `..` и архив больше 80 МБ.
4. Если тег не новее установленной версии, печатает «Установлена актуальная версия» и выходит с кодом 0.
5. `scripts/update.sh` снимает tar-снимок и `pg_dump` **до** копирования новых файлов. `.env`, `.env.*`, `.rollback` и `.git` не затираются.
6. Затем идёт сборка и `scripts/doctor.sh`. Ошибка запускает откат к снимку, снятому до копирования.

Панель только показывает статус: `GET /api/admin/github-update`. Контейнер API архив не распаковывает. Cron администратор включает сам.

На установке **2.10.0** скрипт обновления копировал файлы до снимка. После перехода на 2.11.0 снимок делается раньше. Первый запуск с диска 2.10.0 ещё использует старый порядок. Следующие запуски уже используют порядок 2.11.0.

The 2.10.0 updater copied files before the snapshot. After 2.11.0 is installed, the snapshot is taken first. The first run from a 2.10.0 disk still uses the old order. Later runs use the 2.11.0 order.
