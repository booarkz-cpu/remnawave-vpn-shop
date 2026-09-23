# Release notes 3.1.6

## Русский

Установщик **3.1.6** открывает админку, Mini App и личный кабинет. Схема остаётся `0038_v2_6_0_platform`. Новых APK и IPA нет: покупатель Android остаётся **2.10.0**, администратор Android — **2.12.0**. Исправления **3.1.5** и **3.1.4** остаются. Production gate по-прежнему требует строку `FULL_E2E_PASS`.

В **3.1.5** API был healthy, а `https://admin.<домен>` отвечал **502**. nginx в контейнерах `admin`, `miniapp` и `cabinet` по-прежнему падал, если не мог создать кэш на read-only корне. Теперь pid и временные каталоги nginx лежат в `/tmp/nginx`, который уже смонтирован как tmpfs. Caddy ждёт, пока эти три сервиса отвечают на HTTP. Корень контейнера остаётся только для чтения.

Если админка уже отвечает 502, базу не сбрасывайте. Обновление: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. Команда `docker compose down -v` стирает тома и здесь не нужна.

Проверка: `curl -fsS https://api.<домен>/health` и открытие `https://admin.<домен>`. В `docker compose ps` сервисы `admin`, `miniapp` и `cabinet` должны быть `Up (healthy)`.

## English

Installer **3.1.6** opens the admin UI, the Mini App, and the user cabinet. The schema stays `0038_v2_6_0_platform`. There is no new APK and no IPA: the Android buyer app stays **2.10.0** and the Android administrator app stays **2.12.0**. The **3.1.5** and **3.1.4** fixes remain. The production gate still requires the line `FULL_E2E_PASS`.

In **3.1.5** the API was healthy while `https://admin.<domain>` answered **502**. nginx in the `admin`, `miniapp`, and `cabinet` containers still exited when it could not create its cache on the read-only root. The pid and the nginx temporary directories now live in `/tmp/nginx`, which is already a tmpfs mount. Caddy waits until those three services answer HTTP. The container root stays read-only.

If the admin UI already answers 502, do not wipe the database. Update with `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`. `docker compose down -v` deletes volumes and is not needed here.

Check with `curl -fsS https://api.<domain>/health` and by opening `https://admin.<domain>`. In `docker compose ps`, `admin`, `miniapp`, and `cabinet` should be `Up (healthy)`.
