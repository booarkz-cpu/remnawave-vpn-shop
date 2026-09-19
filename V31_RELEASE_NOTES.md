# V31 Production Release

## One-step installation
- Added root `install.sh` wrapper: `sudo bash install.sh`.
- Installer generates `.env` automatically; no manual file editing is required.
- Frontend `package-lock.json` files are generated automatically in a disposable Node container before build. This keeps the release archive free of generated dependency trees while allowing strict `npm ci` builds.
- Docker runtime image digests are resolved automatically and written to both `.env.images` and `.env`, preventing Compose from silently falling back to mutable tags.
- Firewall remains strict: SSH, TCP 80/443 and UDP 443 only.

## Hardening fixes
- Fixed digest pinning integration with plain `docker compose up`.
- Switched monetary Pydantic/model annotations to `Decimal` to avoid binary floating-point handling of prices.
- Installer validates the primary domain.
- Existing V30 regression suite remains mandatory.

## Validation
- 55 existing tests plus V31 regression tests.
- Python compile, shell syntax and Compose parsing checked.
- Live Docker/provider/Remnawave integration is not executable in the build environment and must be run on staging.
