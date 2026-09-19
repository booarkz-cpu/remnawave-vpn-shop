# V32 Final Production Hardening

V32 closes the remaining audit findings from V29: remote-first Remnawave extension verification, fail-closed rollback, strict withdrawal/refund state transitions, worker identity consistency, production image pinning enforcement, frontend lockfile enforcement, release signature verification tooling, and refund revoke recovery.

## Validation
- 55 automated tests pass in the offline validation environment.
- Python compile and shell syntax checks pass.
- Docker runtime and third-party payment/Remnawave sandboxes must still be exercised on staging.

## Important
Frontend lockfiles are mandatory in production Docker builds. This release does not fabricate lockfiles without registry access. Run `npm install`/`npm ci` in a connected build environment, commit the resulting `package-lock.json` files, then build.
