# Browser (end-to-end) tests

Playwright tests that drive the real UI against the running stack: authentication and the forced password change, the vulnerability form, the Hub (filters, drawer, row/batch actions), the report editor and its lock, dispatch and exports, the vulnerability lifecycle, and the admin pages. They exist mainly to make UI refactors (theming, layout) safe.

## Run them

The stack must be up (`docker compose up -d`). The tests run inside the official Playwright image, on the Compose network, and reach the app through nginx:

```bash
docker run --rm --network portal_default \
  -v "$PWD/e2e:/e2e" -w /e2e \
  mcr.microsoft.com/playwright:v1.49.0-noble \
  sh -c "npm install --no-audit --no-fund && npx playwright test"
```

(On Windows Git Bash prefix the command with `MSYS_NO_PATHCONV=1` and use `$(cygpath -w "$PWD/e2e")` for the mount.)

Useful variations: `npx playwright test tests/hub.spec.js`, `npx playwright test -g "dispatch"`.

| Variable | Default | Meaning |
|---|---|---|
| `E2E_BASE_URL` | `http://nginx:80` | where the app is |
| `E2E_ADMIN_USER` / `E2E_ADMIN_PASSWORD` | `admin` / `admin` | an admin account on that stack |

Against the production-style stack use `E2E_BASE_URL=https://nginx` (self-signed certificates are accepted) — note that its Content-Security-Policy forbids `eval`, which a few Playwright helpers use.

## Notes

- Tests run **serially** (`workers: 1`) and create what they need through the API, with names starting `e2e-`. Users are created per spec file; nothing relies on `alice`/`bob`.
- Cleanup soft-deletes what it can. Dispatched reports and the users/keys the tests create cannot be removed through the app, so a dev database slowly collects `e2e-…` rows. To wipe them:
  ```sql
  update vulnerabilities set deleted_at = now() where deleted_at is null and identifier like 'e2e-%';
  update reports set deleted_at = now() where deleted_at is null and name like 'e2e-%';
  update users set is_active = false where username like 'e2e-%';
  update api_keys set revoked_at = now() where revoked_at is null and label like 'e2e-%';
  ```
- The API-level tests live in `backend/tests` (pytest). Those cover the rules; these cover that the screens expose them correctly.
