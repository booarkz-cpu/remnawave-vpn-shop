# Release notes 3.1.5

## Русский

Установщик **3.1.5** поднимает админку, Mini App и личный кабинет. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android — **2.12.0**. Исправления **3.1.4**, **3.1.3** и **3.1.2** остаются. Production gate по-прежнему требует строку `FULL_E2E_PASS`.

В **3.1.4** API становился healthy, а контейнеры `admin`, `miniapp` и `cabinet` уходили в `Restarting (1)`. nginx писал `mkdir() "/var/cache/nginx/client_temp" failed (30: Read-only file system)`. Caddy из-за этого отвечал 502 и `lookup admin on 127.0.0.11:53: server misbehaving`. Корень контейнера по-прежнему только для чтения. Для nginx добавлены tmpfs `/var/cache/nginx` и `/run`. Установщик дожидается, что эти три сервиса не в `restarting`, и печатает их логи, если они падают. Для Redis выставляется `vm.overcommit_memory=1`.

Проверка API: `curl -fsS https://api.ВАШ-ДОМЕН/health`. Команда называется `curl`.

Если **3.1.4** уже стоит и API healthy, базу не сбрасывайте. Обновление: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Команда `docker compose down -v` стирает тома и здесь не нужна.

## English

Installer **3.1.5** starts the admin UI, the Mini App, and the user cabinet. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The **3.1.4**, **3.1.3**, and **3.1.2** fixes remain. The production gate still requires the line `FULL_E2E_PASS`.

In **3.1.4** the API became healthy while `admin`, `miniapp`, and `cabinet` stayed in `Restarting (1)`. nginx logged `mkdir() "/var/cache/nginx/client_temp" failed (30: Read-only file system)`. Caddy then answered 502 with `lookup admin on 127.0.0.11:53: server misbehaving`. The container root stays read-only. nginx now has tmpfs mounts for `/var/cache/nginx` and `/run`. The installer waits until those three services are not `restarting` and prints their logs when they crash. Redis gets `vm.overcommit_memory=1`.

Check the API with `curl -fsS https://api.YOUR-DOMAIN/health`. The command is `curl`.

If **3.1.4** is already installed and the API is healthy, do not wipe the database. Update with `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. `docker compose down -v` deletes volumes and is not needed here.
