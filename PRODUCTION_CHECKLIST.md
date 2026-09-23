# Production checklist 3.1.6

## Русский

Версия **3.1.6** переносит pid и кэш nginx админки, Mini App и кабинета в `/tmp/nginx`, чтобы `https://admin.<домен>` не отвечал 502. Схема и APK те же. Пошаговая установка — `INSTALL_STEPS.md`, панели — раздел 9.20 `INSTRUCTION.md`. Production gate по-прежнему требует `FULL_E2E_PASS` (раздел 9.15). Живой VPS для 3.1.6 не запускался.

### Прогон 3.1.6 на этом хосте

23 сентября 2026. `deploy/nginx/nginx.conf` задаёт пути внутри `/tmp/nginx`. Compose монтирует его в три панели и ставит healthcheck `GET /`. Docker на хосте сборки недоступен, поэтому контейнер nginx здесь не стартовал.

Версия **3.1.5** даёт nginx в админке, Mini App и кабинете временные каталоги `/var/cache/nginx` и `/run`, поэтому эти контейнеры не остаются в `Restarting` на read-only корне. В **3.1.4** Caddy отвечал 502, пока API уже был healthy. Схема и APK те же. Пошаговая установка — `INSTALL_STEPS.md`, панели — раздел 9.19 `INSTRUCTION.md`. Production gate по-прежнему требует `FULL_E2E_PASS` (раздел 9.15). Записи прогонов 3.1.4 и старше ниже остаются фактами тех хостов. Живой VPS, firewall, S3, SMTP, Xcode и установка на телефон для 3.1.5 не запускались.

### Прогон 3.1.5 на этом хосте

23 сентября 2026. `docker-compose.yml` для `admin`, `miniapp` и `cabinet` содержит tmpfs `/var/cache/nginx` и `/run` при `read_only: true`. `bash -n` прошёл для `install.sh` и `deploy/install-vps.sh`. `MEDIA_DIR=/tmp/media python3 -m pytest -q` завершился с кодом 0: 355 тестов. Живой контейнер nginx в этом прогоне не запускался: Docker на хосте сборки недоступен.

Версия **3.1.4** не даёт backend и worker одновременно создавать `alembic_version`. В **3.1.3** проигравший процесс завершал контейнер API, и установка останавливалась на `installation failed at line 382`. Схема и APK те же. Пошаговая установка — `INSTALL_STEPS.md`, запуск — раздел 9.18 `INSTRUCTION.md`. Production gate по-прежнему требует `FULL_E2E_PASS` (раздел 9.15). Записи прогонов 3.1.3 и старше ниже остаются фактами тех хостов. Живой VPS, firewall, S3, SMTP, Xcode и установка на телефон для 3.1.4 не запускались.

### Прогон 3.1.4 на этом хосте

23 сентября 2026. Два параллельных `alembic upgrade head` на пустой базе PostgreSQL 16 оба завершились с кодом 0 после `pg_advisory_xact_lock`. До блокировки второй процесс падал на `pg_type_typname_nsp_index`. `bash -n` прошёл для `install.sh` и `deploy/install-vps.sh`. `MEDIA_DIR=/tmp/media python3 -m pytest -q` завершился с кодом 0: 352 теста. Живой VPS и кассы в этом прогоне не запускались.

Версия **3.1.3** чинит установку через `curl | bash`: вопросы читаются с терминала SSH. В **3.1.2** первый вопрос завершался `installation failed at line 34`. Схема и APK те же, что у **3.1.2**, **3.1.1**, **3.1.0** и **3.0.1**. Пошаговая установка — `INSTALL_STEPS.md`, установщик — раздел 9.17 `INSTRUCTION.md`. Production gate по-прежнему требует `FULL_E2E_PASS` (раздел 9.15). Записи прогонов 3.1.2, 3.1.1 и 3.1.0 ниже остаются фактами тех хостов. Docker, `scripts/doctor.sh`, живые кассы, firewall, S3, SMTP, Xcode и установка на телефон для 3.1.3 не запускались.

### Прогон 3.1.3 на этом хосте

23 сентября 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` завершился с кодом 0: 347 тестов. `bash -n` прошёл для `install.sh` и `deploy/install-vps.sh`. Отдельный прогон `prompt` через канал и pty получил ответ `vpn.example.com` и не напечатал `installation failed at line 34`. Живой VPS, Docker и кассы в этом прогоне не запускались.

Версия **3.1.2** закрывает утечки учётных данных VPN и текста исключений в ответах панели. Схема и APK те же, что у **3.1.1**, **3.1.0**, **3.0.1** и **3.0.0-realise**. Пошаговая установка — `INSTALL_STEPS.md`, панель — раздел 9.16 `INSTRUCTION.md`. Production gate по-прежнему требует `FULL_E2E_PASS` (раздел 9.15). Записи прогонов 3.1.1 и 3.1.0 ниже остаются фактами тех хостов и не отмечают заново пункты, которые на живом VPS не запускались. Docker, `scripts/doctor.sh`, живые кассы, firewall, S3, SMTP, Xcode и установка на телефон для 3.1.2 не запускались.

### Прогон 3.1.2 на этом хосте

23 сентября 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` завершился с кодом 0: 342 теста. `bash -n` прошёл для `install.sh`, `deploy/install-vps.sh`, `scripts/build-release.sh` и обоих файлов `staging-e2e.sh`. Живой API, Docker и кассы в этом прогоне не запускались.

Версия **3.1.1** сохраняет секреты staging при повторном сохранении, печатает `[CHECKOUT]` и требует `FULL_E2E_PASS` для кнопки **Разрешить реальные платежи**. Схема и APK те же, что у **3.1.0**, **3.0.1** и **3.0.0-realise**. Пошаговая установка — `INSTALL_STEPS.md`, панель — раздел 9.15 `INSTRUCTION.md`. Запись прогона 3.1.0 ниже остаётся фактом того хоста и не отмечает заново пункты, которые на живом VPS не запускались. Docker, `scripts/doctor.sh`, живые кассы, firewall, S3, SMTP, Xcode и установка на телефон для 3.1.1 не запускались.

### Прогон 3.1.1 на этом хосте

23 сентября 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` завершился с кодом 0: 338 тестов. `bash -n` прошёл для `install.sh`, `deploy/install-vps.sh` и обоих файлов `staging-e2e.sh`. Живой API, Docker и кассы в этом прогоне не запускались.

Этот файл — порядок выкладки на VPS и запись прогона на хосте сборки от 22 сентября 2026. Пункты раздела «Порядок на VPS» остаются открытыми, пока их не выполнит администратор на своём сервере. Раздел «Прогон на хосте сборки» отмечает только то, что реально запускалось здесь.

Покупательский APK остаётся `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). Администраторский APK остаётся `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120). Голова миграции остаётся `0038_v2_6_0_platform`.

### Порядок на VPS

#### Перед выкладкой
- [ ] Сгенерировать уникальный `APP_SECRET` длиной от 32 символов.
- [ ] Задать `DB_PASSWORD` и секреты платёжных провайдеров.
- [ ] Задать `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN` и `CABINET_DOMAIN`.
- [ ] Настроить файрвол: SSH, TCP 80/443 и UDP 443.
- [ ] Настроить S3/R2/B2, если нужна внешняя копия.
- [ ] Настроить оповещения Telegram и SMTP.
- [ ] Запустить `scripts/preflight.sh`.
- [ ] Запустить `scripts/security-scan.sh`.
- [ ] Запустить `scripts/integration-test.sh` на staging с Docker.

#### Первый запуск
- [ ] `docker compose config` проходит.
- [ ] `docker compose up -d` проходит.
- [ ] `scripts/doctor.sh` показывает здоровье API.
- [ ] В центре восстановления виден heartbeat воркера.
- [ ] Администратор включает 2FA в разделе безопасности. До настройки 2FA не требуется.
- [ ] Создать и проверить резервную копию.
- [ ] Проверить и выполнить тестовое восстановление на staging.

#### Платёж без живых касс
- [ ] `PAYMENTS_SANDBOX=true`, секреты живых касс пустые.
- [ ] Создать один обычный включённый тариф.
- [ ] `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh`.
- [ ] В `/api/public/servers` нет полей адреса, токена и пароля.
- [ ] По желанию собрать тариф в конструкторе и купить одну комбинацию из кабинета с провайдером `sandbox`.

#### Скачивание приложений 2.13.0
- [ ] Загрузить APK на карточку покупателя и APK администратора. Файл не больше 80 МБ и начинается с заголовка ZIP.
- [ ] В кабинете нажать **Скачать**. Ответ — пакет покупателя. `GET /api/public/apps/android-admin/download` отвечает 404.
- [ ] В панели «Приложения» скачать карточку администратора. Сессия зрителя может скачать. Сессия без `manage_content` не может загрузить файл.
- [ ] Сохранить тексты карточки и убедиться, что загруженный файл на месте.
- [ ] Файл на диске не лежит в каталоге `/media/`.

#### Рассылка Telegram 2.12.0
- [ ] `BOT_TOKEN` задан, процесс бота запущен. API только ставит строку в очередь.
- [ ] Оператор ставит короткое HTML-сообщение аудитории `inactive` или тестовой аудитории из панели «Маркетинг» и из вкладки «Рассылка» приложения администратора.
- [ ] `GET /api/admin/marketing` показывает `queued`, затем `sending`, затем `completed` со `sent_count` и `failed_count`.
- [ ] Зритель получает 403 на `POST /api/admin/broadcasts`.
- [ ] Повтор используется только для `sending` или `failed`. Завершённая строка остаётся завершённой.
- [ ] Установить `remnawave_vpn_shop_android_admin_2_12_0.apk` после проверки `.sha256`. Покупательский APK остаётся `remnawave_vpn_shop_android_user_2_10_0.apk`.

#### Обновление с GitHub 2.11.0
- [ ] Команда в панели «Релизы»: `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
- [ ] После обновления на месте остаются `.env`, `.env.*`, `.rollback` и `.git`.
- [ ] Cron выключен, пока администратор сам не выберет расписание.
- [ ] APK покупателя и администратора остаются файлами прежних релизов. Этот чеклист их не подменяет.

#### Android APK 2.10.0 и 2.9.0
- [ ] Скачать APK 2.10.0 и 2.9.0 с релиза GitHub и сверить `.sha256`.
- [ ] Сверить SHA-256 сертификата подписи с `RELEASE_NOTES_V2_10_0.md`. Отладочный APK 2.9.0 снять перед установкой 2.10.0.
- [ ] Войти и убедиться, что сессия шлёт User-Agent `RemnawaveShop-Android-User/2.10.0` или `RemnawaveShop-Android-Admin/2.10.0`. Сохранённый токен запрашивает биометрию или PIN устройства.
- [ ] `GET /api/me/devices` не содержит `device_key` и `last_ip`.
- [ ] На хосте запускать `sudo bash /opt/vpn-shop/scripts/update-from-github.sh` после чтения команды во вкладке релизов. Cron оставить выключенным.
- [ ] Проекты iOS открывать в Xcode на macOS, когда нужна сборка на устройство. IPA в релизе нет.

#### Каталог приложений 2.8.0
- [ ] В панели «Приложения» сохранить русский и английский тексты. Кабинет показывает только включённые карточки покупателя.
- [ ] Загрузить логотип и увидеть его в шапке кабинета. Ссылка не на `https` отклоняется.
- [ ] `GET /api/public/apps` не содержит карточку администратора, а путь логотипа начинается с `/media/`.

#### Мобильные приложения 2.7.0
- [ ] Собрать `mobile/android-user` и `mobile/android-admin` в Android Studio и два проекта Xcode в `mobile/ios-user` и `mobile/ios-admin`.
- [ ] Указать API с `https://`. Адрес `http://` принимается только для localhost, 127.0.0.1 и 10.0.2.2.
- [ ] Войти из приложения покупателя и увидеть `access_token`, потому что `X-Shop-Client` равен `android-user` или `ios-user`. Повторить из браузера и увидеть JSON без `access_token`.
- [ ] Переключить RU/EN и убедиться, что те же экраны перезагружаются.
- [ ] Открыть серверы и убедиться, что в строках нет адреса, токена и пароля.
- [ ] Из приложения администратора открыть сводку платформы и убедиться, что в ней нет токена агента и секрета вебхука.

#### Платформа 2.6.0
- [ ] Открыть «Платформа» и загрузить сводку без токенов агентов и секретов вебхуков.
- [ ] Оставить `auto_hard_block` выключенным, пока пороги оценки не проверены.
- [ ] Создать агента узла, скопировать токен один раз и запустить `scripts/node-agent.py` с `SHOP_API_BASE` и `AGENT_TOKEN`.
- [ ] Оставить `AGENT_APPLY_TC` пустым, пока интерфейс узла неизвестен. `AGENT_APPLY_TC=1` и `AGENT_IFACE` задавать только для одного глобального адреса.
- [ ] Для вебхуков использовать публичный HTTPS. В доставках виден статус, а не текст исключения.
- [ ] При настроенном SMTP отправить тест и убедиться, что письмо пришло только администратору, который нажал кнопку.
- [ ] Снять `/metrics` с `METRICS_TOKEN` и при необходимости импортировать `deploy/grafana/vpnshop-platform.json`.

#### Живой платёж
- [ ] Создать один тестовый платёж.
- [ ] Подтвердить статус провайдера и вебхук.
- [ ] Подтвердить ровно одну операцию выдачи.
- [ ] Подтвердить пользователя и подписку в Remnawave.
- [ ] Повторить вебхук. Вторая выдача не создаётся.
- [ ] На staging вызвать таймаут и повтор. Сверка завершает исходную операцию.
- [ ] Проверить запрос, разбор и подтверждение возврата.

#### Безопасность
- [ ] Порты PostgreSQL, Redis и backend не опубликованы в интернет.
- [ ] `APP_SECRET_PREVIOUS` держать только на время контролируемой смены секрета.
- [ ] Периодически менять токен метрик.
- [ ] Просматривать журнал аудита и сессии администраторов.
- [ ] Копия с `.env` хранится в зашифрованном виде.
- [ ] Проверять место на диске и срок сертификата.

#### Обновление и откат
- [ ] Запустить `scripts/update.sh` или `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
- [ ] Снимок до обновления существует.
- [ ] Миграция и проверка здоровья проходят.
- [ ] Если здоровье не сходится, запустить `scripts/rollback.sh` и проверить здоровье снова.

### Прогон на хосте сборки

Хост сборки — эта виртуальная машина, без Docker, без Xcode, без живых касс, без SMTP, без S3 и без телефона. Локальные PostgreSQL 16 и Redis 7 подняты вручную. API слушает `127.0.0.1:8000`.

- [x] `alembic upgrade head` на пустой базе дошёл до `0038_v2_6_0_platform`. Колонка `alembic_version.version_num` — `VARCHAR(128)`.
- [x] `GET /health` вернул `ok=true`, `version=3.0.0-realise`, `redis=true`, `database=true`.
- [x] Вход администратора в браузерный JSON (`POST /api/admin/auth/login`) вернул 200 и поля `email`, `mfa_enabled`, `role`. Поля `access_token` в JSON нет.
- [x] Создание тарифа вернуло идентификатор. Журнал аудита принял цену `Decimal` и `request_id`.
- [x] `GET /api/public/servers` вернул `ok=false`, ошибку «Remnawave недоступен» и пустой список узлов. В ответе нет адреса, имени хоста, токена и пароля.
- [x] Маленький ZIP загружен на `POST /api/admin/apps/android-user/file`. В JSON есть `has_file`, имени файла нет. В `/tmp/media` файлов 0, в `/tmp/app-packages` файл 1.
- [x] `GET /api/public/apps/android-admin/download` — 404. `GET /api/public/apps/android-user/download` — 200, 147 байт.
- [x] `Content-Length: 14000000` на `POST /api/payments/create` — 413 до чтения тела. Тот же размер на `POST /api/admin/apps/android-user/file` — 401 до чтения тела. Размер 80 МБ + 1 байт на загрузке пакета — 413.
- [x] Зритель на `POST /api/admin/broadcasts` получил 403 «Insufficient permissions». Администратор без `BOT_TOKEN` получил 503 «BOT_TOKEN is not configured».
- [x] `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh` прошёл здоровье, публичный конфиг, меню кабинета (6 пунктов), регистрацию и создание sandbox-платежа. Завершение `POST /api/payments/sandbox/complete` ответило HTTP 500: `REMNAWAVE_URL` пустой, выдача обращается к Remnawave. Скрипт завершился с кодом 22. Полный пункт чеклиста из-за этого не закрыт.
- [x] В `scripts/update.sh` снимок `pre-update-$STAMP.tar.gz` стоит раньше `UPDATE_STAGE`. В скрипте есть `--exclude='./.env'` и `pg_dump`. Сам `update.sh` на VPS не запускался.
- [x] `bash -n` для `install.sh`, `deploy/*.sh` и `scripts/*.sh` прошёл.
- [x] `scripts/security-scan.sh` завершился с кодом 0. `compileall` прошёл. `npm audit --omit=dev --audit-level=high` для `admin`, `miniapp` и `cabinet` — 0 уязвимостей после подъёма Vite до `7.3.6`. Предупреждения: нет `pip-audit`, Docker, `trivy` и `syft`.
- [x] Сборки `npm run build` для `admin`, `miniapp` и `cabinet` прошли на Vite `7.3.6`.
- [x] `scripts/preflight.sh` завершился с кодом 0: 328 тестов прошли, `compileall` прошёл. Docker на хосте нет, поэтому `docker compose config` внутри preflight не вызывался.
- [ ] `docker compose config`, `docker compose up`, `scripts/integration-test.sh` и `scripts/doctor.sh` не запускались: Docker на этом хосте нет.
- [ ] Файрвол, S3, SMTP, живые кассы, Xcode, установка APK на телефон, резервная копия и тестовое восстановление не выполнялись.

### Прогон 3.1.0 на этом хосте

23 сентября 2026. Та же машина: PostgreSQL 16, Redis 7, API `127.0.0.1:8000` после перезапуска на коде 3.1.0. Пункты «Порядок на VPS» остаются открытыми.

- [x] `alembic_version` уже `0038_v2_6_0_platform`. Новой миграции нет.
- [x] `GET /health` вернул `ok=true`, `version=3.1.0`, `redis=true`, `database=true`.
- [x] `GET /api/plans` не содержит `remnawave_profile_id`. `GET /api/admin/plans` это поле сохраняет.
- [x] `GET /api/public/apps/install` вернул карточки `android-user` и `ios-user`, официальные ссылки `android-user` и `android-admin` и по 4 шага на русском и английском.
- [x] Вход администратора вернул `email`, `mfa_enabled`, `role`. Поля `access_token` нет. Вход покупателя из браузера тоже без `access_token`.
- [x] `GET /api/public/servers` вернул `ok=false`. В ответе нет адреса, токена и пароля.
- [x] Маленький ZIP загружен на карточку покупателя. В JSON есть `has_file` и SHA-256 из 64 символов, ключа `file` нет. В каталоге media файлов 0, в `app-packages` файл 1.
- [x] `GET /api/public/apps/android-admin/download` — 404. `GET /api/public/apps/android-user/download` — 200.
- [x] `Content-Length: 14000000` на `POST /api/payments/create` — 413. Тот же размер на загрузке пакета — 401. Размер 80 МБ + 1 байт — 413.
- [x] Покупатель без подписки: `GET /api/me/auto-renew` вернул `last_error=null`, `GET /api/me/subscription-file` — 404 «Subscription is not available».
- [x] `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh` прошёл здоровье версии 3.1.0, публичный конфиг, меню кабинета (6 пунктов), регистрацию и создание sandbox-платежа. `POST /api/payments/sandbox/complete` ответил HTTP 500, потому что выдача обращается к Remnawave. Скрипт завершился с кодом 22. Пункт чеклиста из-за этого не закрыт.
- [x] `bash -n` для `install.sh`, `deploy/*.sh` и `scripts/*.sh` прошёл.
- [x] `scripts/security-scan.sh` завершился с кодом 0. `npm audit --omit=dev --audit-level=high` для `admin`, `miniapp` и `cabinet` — 0 уязвимостей. Предупреждения: нет `pip-audit`, Docker, `trivy` и `syft`.
- [x] `scripts/preflight.sh` завершился с кодом 0: 333 теста. `docker compose config` не вызывался.
- [ ] `docker compose config`, `docker compose up`, `scripts/integration-test.sh` и `scripts/doctor.sh` не запускались.
- [ ] Файрвол, S3, SMTP, живые кассы, Xcode, телефон, резервная копия и восстановление не выполнялись. Повтор зрителя на рассылке в этом прогоне не делался.

## English

Version **3.1.6** moves the admin, Mini App, and cabinet nginx pid and cache to `/tmp/nginx`, so `https://admin.<domain>` does not answer 502. The schema and the APKs stay the same. The step-by-step install is `INSTALL_STEPS.md` and the panels are section 9.20 of `INSTRUCTION.md`. The production gate still requires `FULL_E2E_PASS` (section 9.15). A live VPS was not run for 3.1.6.

### 3.1.6 build-host run

23 September 2026. `deploy/nginx/nginx.conf` sets paths under `/tmp/nginx`. Compose mounts it into the three panels and adds a `GET /` healthcheck. Docker is not available on the build host, so an nginx container was not started here.

Version **3.1.5** gives nginx in the admin UI, Mini App, and cabinet temporary directories `/var/cache/nginx` and `/run`, so those containers do not stay in `Restarting` on a read-only root. In **3.1.4** Caddy answered 502 while the API was already healthy. The schema and the APKs stay the same. The step-by-step install is `INSTALL_STEPS.md` and the panels are section 9.19 of `INSTRUCTION.md`. The production gate still requires `FULL_E2E_PASS` (section 9.15). The 3.1.4 and older run records below stay facts of those hosts. A live VPS, the firewall, S3, SMTP, Xcode, and a phone install were not run for 3.1.5.

### 3.1.5 build-host run

23 September 2026. `docker-compose.yml` for `admin`, `miniapp`, and `cabinet` contains tmpfs `/var/cache/nginx` and `/run` with `read_only: true`. `bash -n` passed for `install.sh` and `deploy/install-vps.sh`. `MEDIA_DIR=/tmp/media python3 -m pytest -q` exited 0: 355 tests. A live nginx container was not started in this run: Docker is not available on the build host.

Version **3.1.4** stops backend and worker from creating `alembic_version` at the same time. In **3.1.3** the losing process exited the API container, and the install stopped at `installation failed at line 382`. The schema and the APKs stay the same. The step-by-step install is `INSTALL_STEPS.md` and the boot fix is section 9.18 of `INSTRUCTION.md`. The production gate still requires `FULL_E2E_PASS` (section 9.15). The 3.1.3 and older run records below stay facts of those hosts. A live VPS, the firewall, S3, SMTP, Xcode, and a phone install were not run for 3.1.4.

### 3.1.4 build-host run

23 September 2026. Two parallel `alembic upgrade head` runs on an empty PostgreSQL 16 database both exited 0 after `pg_advisory_xact_lock`. Before the lock, the second process failed on `pg_type_typname_nsp_index`. `bash -n` passed for `install.sh` and `deploy/install-vps.sh`. `MEDIA_DIR=/tmp/media python3 -m pytest -q` exited 0: 352 tests. A live VPS and the gateways were not part of this run.

Version **3.1.3** fixes a `curl | bash` install: questions are read from the SSH terminal. In **3.1.2** the first question ended with `installation failed at line 34`. The schema and the APKs stay the same as **3.1.2**, **3.1.1**, **3.1.0**, and **3.0.1**. The step-by-step install is `INSTALL_STEPS.md` and the installer fix is section 9.17 of `INSTRUCTION.md`. The production gate still requires `FULL_E2E_PASS` (section 9.15). The 3.1.2, 3.1.1, and 3.1.0 run records below stay facts of those hosts. Docker, `scripts/doctor.sh`, live gateways, the firewall, S3, SMTP, Xcode, and a phone install were not run for 3.1.3.

### 3.1.3 build-host run

23 September 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` exited 0: 347 tests. `bash -n` passed for `install.sh` and `deploy/install-vps.sh`. A separate `prompt` run through a pipe and a pty accepted `vpn.example.com` and did not print `installation failed at line 34`. A live VPS, Docker, and cashiers were not started in this run.

Version **3.1.2** closes leaks of VPN credentials and exception text in panel responses. The schema and the APKs stay the same as **3.1.1**, **3.1.0**, **3.0.1**, and **3.0.0-realise**. The step-by-step install is `INSTALL_STEPS.md` and the panel changes are section 9.16 of `INSTRUCTION.md`. The production gate still requires `FULL_E2E_PASS` (section 9.15). The 3.1.1 and 3.1.0 run records below stay facts of those hosts and do not mark live-VPS items done again. Docker, `scripts/doctor.sh`, live gateways, the firewall, S3, SMTP, Xcode, and a phone install were not run for 3.1.2.

### 3.1.2 build-host run

23 September 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` exited 0: 342 tests. `bash -n` passed for `install.sh`, `deploy/install-vps.sh`, `scripts/build-release.sh`, and both `staging-e2e.sh` files. The live API, Docker, and cashiers were not started in this run.

Version **3.1.1** keeps staging secrets on a later save, prints `[CHECKOUT]`, and requires `FULL_E2E_PASS` for **Разрешить реальные платежи** (Allow live payments). The schema and the APKs stay the same as **3.1.0**, **3.0.1**, and **3.0.0-realise**. The step-by-step install is `INSTALL_STEPS.md` and the panel order is section 9.15 of `INSTRUCTION.md`. The 3.1.0 run record below stays a fact of that host and does not mark live-VPS items done again. Docker, `scripts/doctor.sh`, live gateways, the firewall, S3, SMTP, Xcode, and a phone install were not run for 3.1.1.

### 3.1.1 build-host run

23 September 2026. `MEDIA_DIR=/tmp/media python3 -m pytest -q` exited 0: 338 tests. `bash -n` passed for `install.sh`, `deploy/install-vps.sh`, and both `staging-e2e.sh` files. The live API, Docker, and cashiers were not started in this run.

This file is the VPS rollout order and the record of the build-host run on 22 September 2026. Items under “VPS order” stay open until an administrator runs them on their own server. “Build-host run” marks only what actually ran here.

The buyer APK stays `remnawave_vpn_shop_android_user_2_10_0.apk` (`versionName` 2.10.0). The administrator APK stays `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120). The migration head stays `0038_v2_6_0_platform`.

### VPS order

#### Before deployment
- [ ] Generate a unique `APP_SECRET` of at least 32 characters.
- [ ] Set `DB_PASSWORD` and the payment-provider secrets.
- [ ] Set `API_DOMAIN`, `ADMIN_DOMAIN`, `APP_DOMAIN` and `CABINET_DOMAIN`.
- [ ] Configure the firewall: SSH, TCP 80/443 and UDP 443.
- [ ] Configure S3/R2/B2 when an off-site copy is required.
- [ ] Configure Telegram and SMTP alerts.
- [ ] Run `scripts/preflight.sh`.
- [ ] Run `scripts/security-scan.sh`.
- [ ] Run `scripts/integration-test.sh` on a Docker staging host.

#### First boot
- [ ] `docker compose config` passes.
- [ ] `docker compose up -d` passes.
- [ ] `scripts/doctor.sh` reports API health.
- [ ] The worker heartbeat is visible in the recovery center.
- [ ] The administrator enables 2FA from Security. 2FA is not required before that setup.
- [ ] Create and verify a backup.
- [ ] Validate and test-restore a backup in staging.

#### Payment smoke test without live gateways
- [ ] Set `PAYMENTS_SANDBOX=true` and leave live gateway secrets empty.
- [ ] Create one ordinary enabled plan.
- [ ] Run `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh`.
- [ ] Confirm `/api/public/servers` has no address, token or password fields.
- [ ] Optionally create a tariff constructor and buy one combination from the cabinet with provider `sandbox`.

#### App downloads 2.13.0
- [ ] Upload an APK on the buyer Android card and an administrator APK on the administrator Android card. Each file is at most 80 MB and starts with a ZIP header.
- [ ] Open the user cabinet and use **Скачать**. The response is the buyer package. `GET /api/public/apps/android-admin/download` returns 404.
- [ ] Open Admin → Приложения and download the administrator card. A viewer session can download. A session without `manage_content` cannot upload.
- [ ] Save the card texts and confirm the uploaded file is still present.
- [ ] Confirm the stored file is not listed under `/media/`.

#### Telegram broadcast 2.12.0
- [ ] `BOT_TOKEN` is set and the bot process is running. The API only queues the row.
- [ ] An operator queues a short HTML message to `inactive` or a test audience from Admin → Маркетинг and from the administrator app tab Рассылка.
- [ ] `GET /api/admin/marketing` shows `queued`, then `sending`, then `completed` with `sent_count` and `failed_count`.
- [ ] A viewer receives 403 on `POST /api/admin/broadcasts`.
- [ ] Retry is used only for `sending` or `failed`. A completed row stays completed.
- [ ] Install `remnawave_vpn_shop_android_admin_2_12_0.apk` after checking its `.sha256`. The buyer APK stays `remnawave_vpn_shop_android_user_2_10_0.apk`.

#### GitHub update 2.11.0
- [ ] The command in Admin → Релизы is `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
- [ ] After an update, `.env`, `.env.*`, `.rollback` and `.git` are still present.
- [ ] Leave cron off unless an administrator chooses a schedule.
- [ ] The buyer and administrator APKs stay the files from their existing releases. This checklist does not replace them.

#### Android APK 2.10.0 and 2.9.0
- [ ] Download the 2.10.0 and 2.9.0 APKs from the GitHub release and check the `.sha256` files.
- [ ] Compare the signing certificate SHA-256 with `RELEASE_NOTES_V2_10_0.md`. Remove a 2.9.0 debug APK before installing 2.10.0.
- [ ] Sign in and confirm the session uses User-Agent `RemnawaveShop-Android-User/2.10.0` or `RemnawaveShop-Android-Admin/2.10.0`. A saved token asks for biometrics or the device PIN.
- [ ] Confirm `GET /api/me/devices` has no `device_key` and no `last_ip`.
- [ ] On the host, run `sudo bash /opt/vpn-shop/scripts/update-from-github.sh` only after reading the command in the releases tab. Leave cron off.
- [ ] Open the iOS projects in Xcode on macOS when a device build is required. The release does not include an IPA.

#### App catalog 2.8.0
- [ ] Open Admin → Приложения, save Russian and English texts, and confirm the user cabinet shows only the enabled buyer cards.
- [ ] Upload a logo and confirm it appears in the cabinet header. A non-https link is rejected.
- [ ] Confirm `GET /api/public/apps` has no administrator card and the logo path starts with `/media/`.

#### Mobile apps 2.7.0
- [ ] Build `mobile/android-user` and `mobile/android-admin` in Android Studio, and the two Xcode projects under `mobile/ios-user` and `mobile/ios-admin`.
- [ ] Point each app at an `https://` API. An `http://` address is accepted only for localhost, 127.0.0.1 and 10.0.2.2.
- [ ] Sign in from a buyer app and confirm the JSON contains `access_token` because `X-Shop-Client` is `android-user` or `ios-user`. Repeat from a browser and confirm the JSON has no `access_token`.
- [ ] Switch RU/EN and confirm the same screens reload.
- [ ] Open Servers and confirm the rows have no address, token or password.
- [ ] From the admin app, load the platform summary and confirm it has no agent token or webhook secret.

#### Platform 2.6.0
- [ ] Open Admin → Платформа and confirm the summary loads without agent tokens or webhook secrets.
- [ ] Leave `auto_hard_block` off until the scoring thresholds are reviewed.
- [ ] Create a node agent, copy the token once, and run `scripts/node-agent.py` with `SHOP_API_BASE` and `AGENT_TOKEN`.
- [ ] Leave `AGENT_APPLY_TC` unset until the node interface is known. Set `AGENT_APPLY_TC=1` and `AGENT_IFACE` only for a single global address.
- [ ] If webhooks are enabled, use a public HTTPS URL. Deliveries show a status, not an exception string.
- [ ] If SMTP is configured, send the test message and confirm it arrives only at the administrator who clicked the button.
- [ ] Scrape `/metrics` with `METRICS_TOKEN` and, if desired, import `deploy/grafana/vpnshop-platform.json`.

#### Live payment
- [ ] Create one test payment.
- [ ] Confirm the provider status and the webhook.
- [ ] Confirm exactly one provisioning operation is created.
- [ ] Confirm the Remnawave user and subscription exist.
- [ ] Replay the webhook. A second provisioning operation is not created.
- [ ] Force a timeout and retry in staging. Reconciliation completes the original operation.
- [ ] Test the refund request, review and confirmation flow.

#### Security
- [ ] Keep PostgreSQL, Redis and backend ports off the public internet.
- [ ] Keep `APP_SECRET_PREVIOUS` only during a controlled rotation window.
- [ ] Rotate the metrics token periodically.
- [ ] Review audit logs and admin sessions.
- [ ] Keep a backup that includes `.env` encrypted.
- [ ] Review disk usage and certificate expiry.

#### Update and rollback
- [ ] Run `scripts/update.sh` or `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
- [ ] Confirm the pre-update snapshot exists.
- [ ] Confirm the migration and health checks pass.
- [ ] If health fails, run `scripts/rollback.sh` and check health again.

### Build-host run

The build host is this virtual machine. It has no Docker, no Xcode, no live gateways, no SMTP, no S3 and no phone. Local PostgreSQL 16 and Redis 7 were started by hand. The API listens on `127.0.0.1:8000`.

- [x] `alembic upgrade head` on an empty database reached `0038_v2_6_0_platform`. The `alembic_version.version_num` column is `VARCHAR(128)`.
- [x] `GET /health` returned `ok=true`, `version=3.0.0-realise`, `redis=true`, `database=true`.
- [x] A browser admin login (`POST /api/admin/auth/login`) returned 200 with `email`, `mfa_enabled` and `role`. The JSON has no `access_token`.
- [x] Creating a plan returned an id. The audit log accepted a `Decimal` price and `request_id`.
- [x] `GET /api/public/servers` returned `ok=false`, the error «Remnawave недоступен», and an empty node list. The payload has no address, hostname, token or password.
- [x] A small ZIP was uploaded to `POST /api/admin/apps/android-user/file`. The JSON has `has_file` and no file name. `/tmp/media` has 0 files and `/tmp/app-packages` has 1 file.
- [x] `GET /api/public/apps/android-admin/download` returned 404. `GET /api/public/apps/android-user/download` returned 200 and 147 bytes.
- [x] `Content-Length: 14000000` on `POST /api/payments/create` returned 413 before the body was read. The same size on `POST /api/admin/apps/android-user/file` returned 401 before the body was read. 80 MB plus 1 byte on the package route returned 413.
- [x] A viewer `POST /api/admin/broadcasts` returned 403 «Insufficient permissions». An administrator with no `BOT_TOKEN` received 503 «BOT_TOKEN is not configured».
- [x] `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh` passed health, public config, the cabinet menu (6 items), registration and sandbox payment creation. `POST /api/payments/sandbox/complete` returned HTTP 500 because `REMNAWAVE_URL` is empty and fulfillment calls Remnawave. The script exited 22. That checklist item stays open.
- [x] In `scripts/update.sh`, the snapshot `pre-update-$STAMP.tar.gz` appears before `UPDATE_STAGE`. The script contains `--exclude='./.env'` and `pg_dump`. `update.sh` itself was not run on a VPS.
- [x] `bash -n` passed for `install.sh`, `deploy/*.sh` and `scripts/*.sh`.
- [x] `scripts/security-scan.sh` exited 0. `compileall` passed. `npm audit --omit=dev --audit-level=high` for `admin`, `miniapp` and `cabinet` reported 0 vulnerabilities after Vite moved to `7.3.6`. Warnings: `pip-audit`, Docker, `trivy` and `syft` are absent.
- [x] `npm run build` for `admin`, `miniapp` and `cabinet` passed on Vite `7.3.6`.
- [x] `scripts/preflight.sh` exited 0: 328 tests passed and `compileall` passed. Docker is absent on this host, so preflight did not call `docker compose config`.
- [ ] `docker compose config`, `docker compose up`, `scripts/integration-test.sh` and `scripts/doctor.sh` were not run. Docker is not installed on this host.
- [ ] The firewall, S3, SMTP, live gateways, Xcode, a phone APK install, a backup and a test restore were not run.

### 3.1.0 build-host run

23 September 2026. The same machine: PostgreSQL 16, Redis 7, and the API on `127.0.0.1:8000` after a restart on the 3.1.0 code. The VPS order stays open.

- [x] `alembic_version` was already `0038_v2_6_0_platform`. There is no new migration.
- [x] `GET /health` returned `ok=true`, `version=3.1.0`, `redis=true`, `database=true`.
- [x] `GET /api/plans` does not contain `remnawave_profile_id`. `GET /api/admin/plans` still includes the field.
- [x] `GET /api/public/apps/install` returned the `android-user` and `ios-user` cards, the official `android-user` and `android-admin` links, and 4 steps in each language.
- [x] Administrator login returned `email`, `mfa_enabled` and `role`. There is no `access_token`. A browser buyer login also has no `access_token`.
- [x] `GET /api/public/servers` returned `ok=false`. The payload has no address, token or password.
- [x] A small ZIP was uploaded to the buyer card. The JSON has `has_file` and a 64-character SHA-256, and no `file` key. The media directory has 0 files and `app-packages` has 1 file.
- [x] `GET /api/public/apps/android-admin/download` returned 404. `GET /api/public/apps/android-user/download` returned 200.
- [x] `Content-Length: 14000000` on `POST /api/payments/create` returned 413. The same size on the package route returned 401. 80 MB plus 1 byte returned 413.
- [x] A buyer without a subscription: `GET /api/me/auto-renew` returned `last_error=null`, and `GET /api/me/subscription-file` returned 404 «Subscription is not available».
- [x] `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh` passed health at version 3.1.0, public config, the cabinet menu (6 items), registration and sandbox payment creation. `POST /api/payments/sandbox/complete` returned HTTP 500 because fulfillment calls Remnawave. The script exited 22. That checklist item stays open.
- [x] `bash -n` passed for `install.sh`, `deploy/*.sh` and `scripts/*.sh`.
- [x] `scripts/security-scan.sh` exited 0. `npm audit --omit=dev --audit-level=high` for `admin`, `miniapp` and `cabinet` reported 0 vulnerabilities. Warnings: `pip-audit`, Docker, `trivy` and `syft` are absent.
- [x] `scripts/preflight.sh` exited 0: 333 tests. `docker compose config` was not called.
- [ ] `docker compose config`, `docker compose up`, `scripts/integration-test.sh` and `scripts/doctor.sh` were not run.
- [ ] The firewall, S3, SMTP, live gateways, Xcode, a phone, a backup and a restore were not run. The viewer broadcast check was not repeated in this run.
