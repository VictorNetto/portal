# Installation Guide

From an empty virtual machine to the first login: the hardware, the operating system, Docker, and the portal itself. Do the steps in order; each one ends with a check.

The portal can be installed on **Ubuntu Server 24.04**, **Oracle Linux 9** or **SUSE Linux Enterprise Server 15 SP7**. Only sections 2 to 4 differ; each system has its own guide for them.

The reasons behind these choices are in [DEPLOYMENT.md](DEPLOYMENT.md). After installation, day-to-day work (updates, certificate renewal, backups, restores, troubleshooting) is in [RUNBOOK.md](RUNBOOK.md).

**Time needed:** about 2 hours, once the items in section 1 are in hand.

---

## Contents

1. [Before you start](#1-before-you-start)
2–4. [Operating system and Docker](#24-operating-system-and-docker): [Ubuntu](install/ubuntu.md), [Oracle Linux](install/oracle-linux.md) or [SLES](install/sles.md)
5. [Get the portal code](#5-get-the-portal-code)
6. [Configure the portal](#6-configure-the-portal)
7. [Install the certificate](#7-install-the-certificate)
8. [Build and start](#8-build-and-start)
9. [First login and checks](#9-first-login-and-checks)
10. [Backups](#10-backups)
11. [Final checklist](#11-final-checklist)

---

## 1. Before you start

### 1.1 Server

For about 20 users. The portal itself is light; the disk grows with uploaded evidence.

| Resource | Minimum |
|---|---|
| Operating system | One of: Ubuntu Server 24.04 LTS, Oracle Linux 9, SUSE Linux Enterprise Server 15 SP7. 64-bit (x86_64) |
| CPU | 4 vCPU |
| Memory | 8 GB |
| Disk | 80 GB SSD (uploaded files are what grows; add space when they do) |
| Network | 1 static internal IP address |

A virtual machine is expected. Nothing else is installed on the server besides Docker: the database, the API and the web server all run in containers.

### 1.2 What to ask IT for

Request these early; some take days.

| Item | Why | Example |
|---|---|---|
| The VM above, with a static IP | Where the portal runs | `10.20.30.40` |
| A DNS **A record** for the portal's name | How users reach it | `portal.redteam.my-organization.com` → `10.20.30.40` |
| A **TLS server certificate** from the organization's PKI, with that name in its **SAN** | HTTPS without browser warnings | `fullchain.pem` + `privkey.pem` |
| **Port 443** (and 80) open from the user networks, including VPN | Users reach the portal | — |
| **Port 22** open from the administrators' network only | SSH administration | — |
| An **SMTP account** that may send to the defense team | Sending reports | `smtp.my-organization.com:587` |
| A place for **backups** outside the VM | Recovery if the VM is lost | NAS share, second server |
| The organization's **NTP server**, if the VM can't reach a public one | Correct times in the audit log | `ntp.my-organization.com` |
| The **HTTP proxy**, if the VM has no direct internet access | Downloading system updates and Docker images | `http://proxy.my-organization.com:3128` |

For **SLES**, also ask for a **registration code**, or the address of the organization's RMT or SUSE Manager server: without one the server gets no updates.

Also ask how the VM itself is backed up (hypervisor snapshots) and how it is restored.

### 1.3 Internet access during installation

The server downloads software only while installing and updating. It must reach:

| Address | For |
|---|---|
| `archive.ubuntu.com`, `security.ubuntu.com` | Ubuntu packages (Ubuntu only) |
| `yum.oracle.com` | Oracle Linux packages (Oracle Linux only) |
| `scc.suse.com`, `updates.suse.com` (or the organization's RMT / SUSE Manager) | SLES registration and packages (SLES only) |
| `download.docker.com` | Docker (Ubuntu and Oracle Linux) |
| `registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com` | Container images (`postgres`, `nginx`, `python`, `node`) |
| `pypi.org`, `files.pythonhosted.org` | Python libraries (built into the API image) |
| `registry.npmjs.org` | JavaScript libraries (built into the web image) |
| `github.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com` | The portal code (or copy it another way, section 5); on SLES, also the Compose plugin |

Once running, the portal makes **no outgoing connections** except to the SMTP server.

### 1.4 Information to have at hand

- The installation image, attached to the VM: `ubuntu-24.04.x-live-server-amd64.iso` (ubuntu.com), `OracleLinux-R9-Ux-x86_64-dvd.iso` (yum.oracle.com/oracle-linux-isos.html), or `SLE-15-SP7-Full-x86_64-GM-Media1.iso` (suse.com, with the organization's account).
- The IP address, subnet (for example `10.20.30.0/24`), gateway and DNS servers for the VM.
- A name for the server (for example `portal-01`) and for the administrator account (for example `portaladm`).
- An SSH key pair on your own machine (`ssh-keygen -t ed25519` if you don't have one).
- A password manager entry to store the secrets created below.

---

## 2–4. Operating system and Docker

Sections 2 to 4 (installing the system, preparing it, installing Docker) depend on the operating system. Follow **one** of these guides, then come back to section 5:

- [Ubuntu Server 24.04 LTS](install/ubuntu.md)
- [Oracle Linux 9](install/oracle-linux.md)
- [SUSE Linux Enterprise Server 15 SP7](install/sles.md)

Everything from section 5 on is the same on all three: the portal runs in containers, so the system only has to provide Docker.

**Which one?** Prefer the system your IT department already supports (hardening baseline, monitoring, patching). If it is your choice:

- **Ubuntu** is what the portal was developed and tested on.
- **Oracle Linux** gets Docker straight from Docker's own repository, like Ubuntu, and its updates are free. SELinux is on, which the guide handles.
- **SLES** uses SUSE's own Docker package (supported by SUSE through the subscription); the Compose plugin is installed by hand, and updated by hand.

---

## 5. Get the portal code

The portal lives in `/opt/portal`.

```bash
sudo mkdir -p /opt/portal && sudo chown portaladm:portaladm /opt/portal
git clone <repository-url> /opt/portal
cd /opt/portal
```

The repository is private. Two ways to give the server read access:

- **Deploy key (recommended):** on the server, `ssh-keygen -t ed25519 -f ~/.ssh/portal_deploy -N ''`; add `~/.ssh/portal_deploy.pub` to the repository's *Settings → Deploy keys* **without** write access; then clone with `GIT_SSH_COMMAND='ssh -i ~/.ssh/portal_deploy' git clone git@github.com:<owner>/portal.git /opt/portal`.
- **No access to GitHub from the server:** on a machine that has it, `git archive --format=tar.gz -o portal.tar.gz main`, copy the file with `scp`, and unpack it with `tar -xzf portal.tar.gz -C /opt/portal`. Updates are done the same way.

**Check:** `ls /opt/portal` shows `docker-compose.prod.yml`, `backend`, `frontend`, `nginx`, `scripts`, `docs`.

---

## 6. Configure the portal

All settings live in one file, `/opt/portal/.env.production`. It holds secrets: it is never committed, and only `portaladm` may read it.

```bash
cd /opt/portal
cp .env.production.example .env.production
chmod 600 .env.production
```

Create two random secrets and store both in the password manager:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # -> JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # -> database password
```

Edit the file (`nano .env.production`) and set:

| Setting | Value |
|---|---|
| `PORTAL_SERVER_NAME` | The DNS name, exactly as in the certificate: `portal.redteam.my-organization.com` |
| `PORTAL_CERT_DIR` | Leave `./certs` |
| `POSTGRES_PASSWORD` | The database password created above |
| `DATABASE_URL` | Replace `CHANGE-ME-long-random` with **the same** database password |
| `JWT_SECRET` | The first secret created above. The portal refuses to start without it, or if it is shorter than 32 characters |
| `FIRST_ADMIN_PASSWORD` | Optional. If empty, a random one is printed once in the logs (section 8). Either way it must be changed at the first login |
| `STORAGE_BACKEND` | Leave `local` (files are kept in a Docker volume on this server) |
| `DISPATCH_TRANSPORT` | `smtp` to send email; `stub` to only log sends while you test |
| `DISPATCH_TO` | The defense team's address |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | From IT. With port 587 keep `SMTP_STARTTLS=true` and `SMTP_SSL=false`; with port 465 set `SMTP_STARTTLS=false` and `SMTP_SSL=true` |

Leave the other lines as they are. Don't put quotes around the values.

> The development accounts and passwords (`admin`/`admin`, sample users) exist only in the development setup. They are never created here, and the sample-data script is not even included in the production images.

---

## 7. Install the certificate

The web server needs two files in `/opt/portal/certs`:

| File | Contents |
|---|---|
| `fullchain.pem` | The server certificate **followed by** the intermediate certificate(s), in that order |
| `privkey.pem` | The private key, **not** protected by a passphrase (the server can't type one at startup) |

```bash
mkdir -p /opt/portal/certs
# copy the files from your machine:  scp fullchain.pem privkey.pem portaladm@10.20.30.40:/opt/portal/certs/
chmod 644 /opt/portal/certs/fullchain.pem
chmod 600 /opt/portal/certs/privkey.pem
```

If IT gave you separate files, build the chain yourself: `cat server.crt intermediate.crt > fullchain.pem`. A `.pfx`/`.p12` file is converted with:

```bash
openssl pkcs12 -in portal.pfx -clcerts -nokeys -out server.crt
openssl pkcs12 -in portal.pfx -cacerts -nokeys -out intermediate.crt
openssl pkcs12 -in portal.pfx -nocerts -nodes -out privkey.pem
cat server.crt intermediate.crt > fullchain.pem
```

**Check** the name, the expiry date, and that the key belongs to the certificate:

```bash
cd /opt/portal/certs
openssl x509 -in fullchain.pem -noout -subject -enddate -ext subjectAltName   # the portal's name must be in the SAN
openssl x509 -in fullchain.pem -noout -pubkey | openssl sha256
openssl pkey -in privkey.pem -pubout | openssl sha256                         # the two hashes must match
```

Put the expiry date in the team calendar, a few weeks early. Renewal is in RUNBOOK §3.

---

## 8. Build and start

Use a short name for the long Compose command (add these two lines to `~/.bashrc` so they survive a logout):

```bash
export PORTAL_ENV_FILE=.env.production
alias dc='docker compose -f docker-compose.prod.yml --env-file .env.production'
```

Then, from `/opt/portal`:

```bash
cd /opt/portal
dc build                                   # 5–15 minutes the first time
dc up -d db                                # the database first
dc run --rm api alembic upgrade head       # create the tables
dc up -d                                   # everything else
dc ps                                      # all four services "Up"; api "healthy" after a few seconds
```

Read the first administrator's password (only if you left `FIRST_ADMIN_PASSWORD` empty):

```bash
dc logs api | grep -i -A2 password
```

**If something fails:** `dc logs api` and `dc logs nginx` show why. The most common causes are in RUNBOOK §6 (missing `JWT_SECRET`, certificate files, a wrong database password).

---

## 9. First login and checks

### 9.1 On the server

```bash
curl -fsS https://portal.redteam.my-organization.com/api/health
# {"status":"ok","environment":"production"}
```

If the name doesn't resolve on the server itself, test with `curl -fsS --resolve portal.redteam.my-organization.com:443:127.0.0.1 https://portal.redteam.my-organization.com/api/health`.

### 9.2 From a user's machine (on the office network **and** on the VPN)

1. `nslookup portal.redteam.my-organization.com` returns the server's IP.
2. Open `http://portal.redteam.my-organization.com`: it redirects to `https://`.
3. The browser shows the padlock with **no warning**. A warning means the name is not in the certificate, the chain is incomplete, or the organization's root certificate is not on that machine.

### 9.3 In the portal

1. Log in as `admin` with the first password. You are taken to the profile page to set a new one; store it in the password manager.
2. In **Administração → Usuários**, create the team's accounts. Each person sets their own password at the first login. Accounts for the defense team use the **Defesa** role.
3. Send a test: create a vulnerability, *Concluir*, *Enviar*. With `DISPATCH_TRANSPORT=smtp` the defense team's mailbox receives it; if delivery fails, the error is shown on the record (fix the `SMTP_*` settings, then `dc up -d api`).
4. Delete the test vulnerability.

The portal's own help is in the profile menu → **Documentação**.

---

## 10. Backups

Set them up **before** the portal holds real findings. The full procedure, including restores, is in RUNBOOK §4–5; the essentials:

1. Mount the backup location from section 1.2 at `/srv/portal-backups` (ask IT for the share and its mount options). Avoid keeping the only copy on the same VM.
2. Create the encryption passphrase, store it in the password manager **and** on the server:
   ```bash
   sudo sh -c 'python3 -c "import secrets; print(secrets.token_urlsafe(32))" > /root/.portal-backup-pass'
   sudo chmod 600 /root/.portal-backup-pass
   ```
   Without this passphrase the backups can't be read. Losing it means losing the backups.
3. Take a first backup by hand and check that the file appears:
   ```bash
   cd /opt/portal
   sudo BACKUP_PASSPHRASE="$(sudo cat /root/.portal-backup-pass)" scripts/backup.sh /srv/portal-backups
   ls -lh /srv/portal-backups
   ```
4. Schedule it every night (`sudo crontab -e`):
   ```
   30 2 * * *  cd /opt/portal && BACKUP_PASSPHRASE="$(cat /root/.portal-backup-pass)" scripts/backup.sh /srv/portal-backups >> /var/log/portal-backup.log 2>&1
   ```
5. **Test a restore** on a separate machine (RUNBOOK §5). A backup that was never restored is not a backup.

---

## 11. Final checklist

- [ ] The VM matches section 1.1; `df -h /` shows the whole disk.
- [ ] SSH works with keys only; password and root logins are refused.
- [ ] The clock is synchronized; automatic security updates are enabled.
- [ ] The firewall (`ufw` or `firewalld`) allows 22 from administrators only, and 80/443.
- [ ] Oracle Linux: SELinux is *Enforcing* and `docker info` lists `selinux`.
- [ ] Docker comes from `download.docker.com` (SLES: the Containers Module); `docker compose version` works; log size is limited.
- [ ] `.env.production` has real secrets, mode `600`, and they are in the password manager.
- [ ] The certificate has the portal's name in its SAN, the full chain, and its expiry date in the calendar.
- [ ] `dc ps` shows four services up; `/api/health` answers from the office and from the VPN, without browser warnings.
- [ ] The first admin password was changed; team accounts exist.
- [ ] A test email reached the defense team.
- [ ] The nightly backup runs, goes outside the VM, and a restore was tested.
- [ ] The passphrase, secrets and admin password are in the password manager.

Next: [RUNBOOK.md](RUNBOOK.md) for updates, everyday operations, certificate renewal and troubleshooting.
