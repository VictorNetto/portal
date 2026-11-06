# Deployment & Networking Plan

How the Red Team Operations Platform is deployed. Target: a single self-hosted Linux VM on the **internal network (LAN/VPN only)**, not public internet. Everything runs in Docker containers, so the environment is identical on the Windows dev machine and the Linux server.

> This is a living plan written while the app is still being built. Commands and files referenced here are created as we go.

---

## 1. Deployment shape

```
                         ┌──────────────────────────────────────────────┐
                         │                 Ubuntu 24.04 VM               │
  user's browser         │                                              │
  https://portal.redteam │   ┌───────────────┐                          │
  .my-organization.com   │   │ nginx (proxy) │  ← ONLY exposed port 443 │
  (LAN / VPN) ───────────────►│   container   │     holds the PKI cert   │
                         │   └───────┬───────┘                          │
                         │           │ routes by URL path               │
                         │   /api/*  ├────────► api   (FastAPI :8000)     │
                         │   /*      └────────► web   (Vue static :80)    │
                         │                                              │
                         │   db (PostgreSQL)   attachments (volume)     │
                         │        ↑ no ports exposed — reached only      │
                         │          internally by api/nginx              │
                         └──────────────────────────────────────────────┘
```

- **Reverse proxy:** nginx, **run as a container** in the Compose stack (not host-installed). Config lives in the repo, versioned with the code; same proxy in dev and prod.
- **Only nginx is exposed** (port 443, + 80 redirecting to 443). `api`, `db`, `web` publish no ports to the network; they talk over Docker's private network by service name (`api`, `db`, …).
- **TLS terminates at nginx.** Internal containers speak plain HTTP.

---

## 2. Server specs (≈20 operators — light workload)

| Resource | Spec |
|---|---|
| OS | Ubuntu Server 24.04 LTS (also documented: Oracle Linux 9, SLES 15 SP7) |
| CPU | 4 vCPU |
| RAM | 8 GB |
| Disk | 80 GB SSD (uploaded attachments are the growth driver — resize if file volume grows) |
| Network | Static internal IP |

The VM needs only **Docker + Docker Compose** installed on the host — no Python, Postgres or Node on the host; those live inside containers. Step-by-step installation, from the bare VM to the first login: [INSTALL.md](INSTALL.md).

---

## 3. DNS + HTTPS (org DNS + org PKI available)

Best case: with the org DNS and PKI, users get `https://portal.redteam.my-organization.com` with a trusted padlock and **no browser warnings** on managed machines (they already trust the org root CA).

**Three things must name the same hostname:**
1. **DNS** `portal.redteam.my-organization.com` → VM static IP (A record).
2. **Certificate** from the org PKI with that FQDN in the **Subject Alternative Name (SAN)** field (not just CN — browsers only check SAN).
3. **nginx** `server_name` set to that FQDN, serving the PKI cert + key.

**Certificate notes:**
- nginx wants the **server cert + intermediate chain concatenated** in the cert file, or some clients get trust errors.
- The **private key** stays on the server, treated as a secret (never in git).
- PKI certs **expire and do not auto-renew** (unlike Let's Encrypt). Ask PKI team the **validity period** and whether **ACME / SCEP / EST auto-enrollment** is available. If ACME is available, automate renewal; otherwise document a manual renewal step + calendar reminder in the runbook.

---

## 4. App-specific proxy details (don't skip)

- **`client_max_body_size`** — nginx defaults to a 1 MB upload cap; the app has attachment/evidence uploads. Set to ~50–100 MB or uploads fail with a confusing `413`.
- **Real client IP** — the audit log (SPEC D8) records IP addresses. nginx must forward the real client IP via `X-Forwarded-For` / `X-Real-IP`, and FastAPI must be configured to trust the proxy, or every audit entry logs nginx's IP instead of the operator's. Correctness issue, not cosmetic.

---

## 5. Security posture (internal ≠ trusted)

LAN/VPN-only removes public-internet hardening (public cert automation, DDoS, aggressive rate-limiting), but **confidential data means internal access is still controlled**: auth, RBAC, and per-read audit logging (D8) all still do real work.
- Restrict firewall so only the LAN/VPN user subnets can reach port 443 on the VM.
- Only nginx is network-exposed; db and api are unreachable from outside the VM.
- **No external egress except the dispatcher** (email now, ServiceNow later). No OneDrive integration or other side channels — the dispatcher is the single sanctioned, audited way data leaves the system. (Operators may *manually* share a final exported report via OneDrive; that is a human action, not a platform feature.)

---

## 6. Responsibilities self-hosting puts on us (a cloud would hide these)

| Responsibility | Plan |
|---|---|
| **Backups** | `pg_dump` + the attachments volume (`scripts/backup.sh`), **encrypted**, to **org-controlled infrastructure** (primary: second internal machine/NAS; fallback: separate disk on same VM). Highest-value ops task — built early, not last. No OneDrive. |
| OS updates | `unattended-upgrades` for security patches + periodic reboots |
| Restart on crash/reboot | Docker `restart: unless-stopped` on every container |
| Monitoring | Start simple: health-check endpoint + reachability alert. Full monitoring post-MVP. |
| Disk filling | Alert on disk usage; uploaded attachments are the growth driver |

---

### Attachment storage and backups

With `STORAGE_BACKEND=local` (the default, decision D9) uploaded files live in the `attachments-data` Docker volume, **not** in PostgreSQL. A backup of the database alone loses every attachment and evidence file, so back up that volume together with the database (and restore them as a pair). With `STORAGE_BACKEND=s3` the files live in the object store, which needs its own backup/replication.

## 7. Deploy loop (once built)

One-time on the server: install Docker, create the production `.env` (real secrets — never in git), obtain + install the PKI cert.

Each release:
1. Get code onto server (`git pull`).
2. `docker compose build`
3. Run DB migrations (Alembic).
4. `docker compose up -d`
5. Verify: `docker compose ps`, `docker compose logs`.

First start prints the seeded admin password to `docker compose logs api` (SPEC §10.1) — grab it, log in, change it.

The exact commands are in [RUNBOOK.md](RUNBOOK.md).

---

## 8. Checklist of asks for IT / infra

1. **VM with Ubuntu 24.04, Oracle Linux 9 or SLES 15 SP7** — 4 vCPU / 8 GB / 80 GB — with a **static internal IP**.
2. **DNS A record**: `portal.redteam.my-organization.com` → that IP.
3. **PKI TLS server certificate** for that FQDN (in **SAN**); confirm **validity period** and whether **ACME/SCEP/EST auto-enrollment** exists.
4. Confirm **port 443 reachable** to the VM from LAN/VPN user networks (firewall/segmentation).
5. Confirm the DNS name **resolves for VPN clients** too (split-horizon check): `nslookup portal.redteam.my-organization.com` from a user machine returns the VM IP.
6. Confirm **VM backup story** at the hypervisor level (and how to restore) — determines how much backup work is ours.
