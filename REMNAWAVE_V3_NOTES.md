# Remnawave v3 integration notes

Based on docs.rw and current v3 API changelog:

- User API uses numeric `id`, not user UUID.
- `POST /api/users` creates a user and no longer accepts a custom UUID.
- `PATCH /api/users` identifies the user by `id`.
- `GET /api/users/{userId}` gets a user.
- `GET /api/users/by-username/{username}` remains available.
- `POST /api/users/{userId}/actions/extend` accepts `{ "days": N }`.
- Subscription lookup: `/api/subscriptions/by-id/{userId}`.
- Connection keys: `/api/subscriptions/connection-keys/{userId}`.
- User list supports `start`/`size`; current documented max is 1000.
- Node installation is Docker-based. The Panel UI generates the node docker-compose.yml; NODE_PORT should be firewall-restricted to the Panel IP.

The exact request schema for your 3.4.4 build should still be verified against its generated API docs before enabling automatic provisioning.
