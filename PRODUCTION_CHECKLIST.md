# V42 Production Checklist

## Before deployment
- [ ] Generate a unique APP_SECRET (>=32 chars).
- [ ] Set DB_PASSWORD and all provider credentials.
- [ ] Set API_DOMAIN, ADMIN_DOMAIN, APP_DOMAIN and CABINET_DOMAIN.
- [ ] Configure strict firewall: SSH + TCP 80/443 + UDP 443 only.
- [ ] Configure S3/R2/B2 if off-site backups are required.
- [ ] Configure Telegram/SMTP alerts.
- [ ] Run `scripts/preflight.sh`.
- [ ] Run `scripts/security-scan.sh`.
- [ ] Run `scripts/integration-test.sh` on a Docker-enabled staging host.

## First boot
- [ ] `docker compose config` passes.
- [ ] `docker compose up -d` passes.
- [ ] `scripts/doctor.sh` reports API health OK.
- [ ] Worker heartbeat is visible in Recovery Center.
- [ ] Admin enables 2FA from Security; it is not forced before setup.
- [ ] Create and verify a backup.
- [ ] Validate and test-restore a backup in staging.

## Payment smoke test without live gateways
- [ ] Set `PAYMENTS_SANDBOX=true` and leave live gateway secrets empty.
- [ ] Create one ordinary enabled plan.
- [ ] Run `SANDBOX_API_BASE=http://127.0.0.1:8000 bash scripts/sandbox-e2e.sh`.
- [ ] Confirm `/api/public/servers` has no address, token or password fields.
- [ ] Optionally create a tariff constructor and buy one combination from the cabinet with provider `sandbox`.

## App downloads 2.13.0
- [ ] Upload an APK on the buyer Android card and an administrator APK on the administrator Android card. Confirm each file is at most 80 MB and starts with a ZIP header.
- [ ] Open the user cabinet and use **Скачать**. The response is the buyer package. `GET /api/public/apps/android-admin/download` returns 404.
- [ ] Open Admin → Приложения and use **Скачать** on the administrator card. A viewer session can download. A session without `manage_content` cannot upload.
- [ ] Save the card texts and confirm the uploaded file is still present.
- [ ] Confirm the stored file is not listed under `/media/`.

## Telegram broadcast 2.12.0
- [ ] `BOT_TOKEN` is set and the bot process is running. The API only queues the row.
- [ ] An operator queues a short HTML message to `inactive` or a test audience from Admin → Маркетинг and from the administrator app tab Рассылка.
- [ ] `GET /api/admin/marketing` shows `queued`, then `sending`, then `completed` with `sent_count` and `failed_count`.
- [ ] A viewer receives 403 on `POST /api/admin/broadcasts`.
- [ ] Retry is used only for `sending` or `failed`. A completed row stays completed.
- [ ] Install `remnawave_vpn_shop_android_admin_2_12_0.apk` (`versionName` 2.12.0, `versionCode` 2120) after checking its `.sha256`. The buyer APK stays `remnawave_vpn_shop_android_user_2_10_0.apk`.

## GitHub update 2.11.0
- [ ] Read the command in Admin → Релизы. It is `sudo bash /opt/vpn-shop/scripts/update-from-github.sh`.
- [ ] Confirm `.env` is still present after a dry understanding of the script. The script keeps `.env`, `.env.*`, `.rollback` and `.git`.
- [ ] Leave cron off unless an administrator chooses a schedule.
- [ ] The buyer and administrator APKs stay the 2.10.0 release files. This checklist does not replace them.

## Android APK 2.10.0
- [ ] Download `remnawave_vpn_shop_android_user_2_10_0.apk` and `remnawave_vpn_shop_android_admin_2_10_0.apk` from the GitHub release and check the `.sha256` files.
- [ ] Compare the signing certificate SHA-256 with `RELEASE_NOTES_V2_10_0.md`. Uninstall a 2.9.0 debug APK once before installing 2.10.0.
- [ ] Sign in and confirm the session uses User-Agent `RemnawaveShop-Android-User/2.10.0` or `RemnawaveShop-Android-Admin/2.10.0`. A saved token asks for biometrics or the device PIN.
- [ ] Confirm `GET /api/me/devices` has no `device_key` and no `last_ip`.
- [ ] On the host, run `sudo bash /opt/vpn-shop/scripts/update-from-github.sh` only after reading the command in the admin releases tab. Leave cron off unless an administrator chooses it.
- [ ] Open the iOS projects in Xcode on macOS when a device build is required. The release does not include an IPA.

## Android APK 2.9.0
- [ ] Download `remnawave_vpn_shop_android_user_2_9_0.apk` and `remnawave_vpn_shop_android_admin_2_9_0.apk` from the GitHub release and check the `.sha256` files.
- [ ] Install with `adb install -r` or by opening the APK after allowing installs from that source.
- [ ] Sign in and confirm the session uses User-Agent `RemnawaveShop-Android-User/2.9.0` or `RemnawaveShop-Android-Admin/2.9.0`.
- [ ] Open the iOS projects in Xcode on macOS when a device build is required. The release does not include an IPA.

## App catalog 2.8.0
- [ ] Open Admin → Приложения, save Russian and English texts, and confirm the user cabinet shows only the enabled buyer cards.
- [ ] Upload a logo and confirm it appears in the cabinet header. Confirm a non-https link is rejected.
- [ ] Confirm `GET /api/public/apps` has no administrator card and the logo path starts with `/media/`.

## Mobile apps 2.7.0
- [ ] Build `mobile/android-user` and `mobile/android-admin` in Android Studio, and the two Xcode projects under `mobile/ios-user` and `mobile/ios-admin`.
- [ ] Point each app at `https://` API. Confirm `http://` is rejected except for localhost, 127.0.0.1 and 10.0.2.2.
- [ ] Sign in from a buyer app and confirm the JSON contains `access_token` only because `X-Shop-Client` is `android-user` or `ios-user`. Repeat from a browser and confirm the JSON has no `access_token`.
- [ ] Switch RU/EN and confirm the same screens reload.
- [ ] Open Servers and confirm the rows have no address, token or password.
- [ ] From the admin app, load the platform summary and confirm it has no agent token or webhook secret.

## Platform 2.6.0
- [ ] Open Admin → Платформа and confirm the summary loads without agent tokens or webhook secrets.
- [ ] Leave `auto_hard_block` off until the scoring thresholds are reviewed.
- [ ] Create a node agent, copy the token once, and run `scripts/node-agent.py` with `SHOP_API_BASE` and `AGENT_TOKEN`.
- [ ] Leave `AGENT_APPLY_TC` unset until the node interface is known. Set `AGENT_APPLY_TC=1` and `AGENT_IFACE` only for a single global address.
- [ ] If webhooks are enabled, use a public HTTPS URL. Confirm deliveries show a status, not an exception string.
- [ ] If SMTP is configured, send the test message and confirm it arrives only at the administrator who clicked the button.
- [ ] Scrape `/metrics` with `METRICS_TOKEN` and, if desired, import `deploy/grafana/vpnshop-platform.json`.

## Payment smoke test
- [ ] Create one test payment.
- [ ] Confirm provider status and webhook.
- [ ] Confirm exactly one provisioning operation is created.
- [ ] Confirm Remnawave user/subscription exists.
- [ ] Replay the webhook; no duplicate provisioning occurs.
- [ ] Force a timeout/retry in staging; reconciliation completes the original operation.
- [ ] Test refund request/review/confirmation flow.

## Security
- [ ] Never expose PostgreSQL/Redis/backend ports publicly.
- [ ] Keep APP_SECRET_PREVIOUS only during a controlled rotation window.
- [ ] Rotate metrics token periodically.
- [ ] Review audit logs and admin sessions.
- [ ] Verify backups are encrypted when `.env` is included.
- [ ] Review disk usage and certificate expiry.

## Update / rollback
- [ ] Run `scripts/update.sh`.
- [ ] Confirm pre-update snapshot exists.
- [ ] Confirm migration + health checks pass.
- [ ] If health fails, run `scripts/rollback.sh` and re-check health.
