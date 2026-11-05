# Installation Guide

From an empty virtual machine to the first login: the hardware, the operating system, Docker, and the portal itself. Do the steps in order; each one ends with a check.

The reasons behind these choices are in [DEPLOYMENT.md](DEPLOYMENT.md). After installation, day-to-day work (updates, certificate renewal, backups, restores, troubleshooting) is in [RUNBOOK.md](RUNBOOK.md).

**Time needed:** about 2 hours, once the items in section 1 are in hand.

---

## Contents

1. [Before you start](#1-before-you-start)
2. [Install Ubuntu Server](#2-install-ubuntu-server)
3. [Prepare the server](#3-prepare-the-server)
4. [Install Docker](#4-install-docker)
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
| Operating system | Ubuntu Server 24.04 LTS, 64-bit (x86_64) |
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
| The **HTTP proxy**, if the VM has no direct internet access | Downloading Ubuntu updates and Docker images | `http://proxy.my-organization.com:3128` |

Also ask how the VM itself is backed up (hypervisor snapshots) and how it is restored.

### 1.3 Internet access during installation

The server downloads software only while installing and updating. It must reach:

| Address | For |
|---|---|
| `archive.ubuntu.com`, `security.ubuntu.com` | Ubuntu packages |
| `download.docker.com` | Docker |
| `registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com` | Container images (`postgres`, `nginx`, `python`, `node`) |
| `pypi.org`, `files.pythonhosted.org` | Python libraries (built into the API image) |
| `registry.npmjs.org` | JavaScript libraries (built into the web image) |
| `github.com` | The portal code (or copy it another way, section 5) |

Once running, the portal makes **no outgoing connections** except to the SMTP server.

### 1.4 Information to have at hand

- Ubuntu Server 24.04 LTS installation image (`ubuntu-24.04.x-live-server-amd64.iso` from ubuntu.com), attached to the VM.
- The IP address, subnet (for example `10.20.30.0/24`), gateway and DNS servers for the VM.
- A name for the server (for example `portal-01`) and for the administrator account (for example `portaladm`).
- An SSH key pair on your own machine (`ssh-keygen -t ed25519` if you don't have one).
- A password manager entry to store the secrets created below.

---

## 2. Install Ubuntu Server

Boot the VM from the ISO. The installer is text-based; move with the arrow keys and **Tab**, choose with **Enter**.

1. **Language:** English (recommended: log messages and online help are in English).
2. **Installer update:** if offered, *Continue without updating* is fine.
3. **Keyboard:** choose your layout (for example *Portuguese (Brazil)*). Use *Identify keyboard* if unsure.
4. **Type of installation:** **Ubuntu Server** (not *minimized*). Leave *Search for third-party drivers* unticked.
5. **Network:** select the network card → *Edit IPv4* → **Manual**, then fill in:
   - Subnet: `10.20.30.0/24`
   - Address: `10.20.30.40`
   - Gateway: `10.20.30.1`
   - Name servers: the organization's DNS servers, separated by commas
   - Search domains: `my-organization.com`

   Save, and check that the card shows the address before continuing.
6. **Proxy:** the organization's proxy if the VM has no direct internet access (`http://proxy.my-organization.com:3128`); otherwise empty.
7. **Ubuntu archive mirror:** keep the default; the installer tests it. If the test fails, the network or proxy is wrong: go back.
8. **Storage:** *Use an entire disk*, with **Set up this disk as an LVM group** ticked. Leave encryption off unless your policy requires it (an encrypted disk asks for a passphrase at every boot, so the server can't restart unattended).

   On the summary screen, **check the size of `ubuntu-lv` (mounted at `/`)**: Ubuntu often uses only part of the disk. If it is smaller than the disk, select it → *Edit* → set the size to the maximum shown → *Save*. (If you miss this, it can be fixed later, section 3.1.)
9. **Confirm** the destructive action: *Continue*.
10. **Profile:**
    - Your name: `Portal Admin`
    - Your server's name: `portal-01`
    - Username: `portaladm`
    - Password: a strong one, stored in the password manager
11. **Ubuntu Pro:** *Skip for now* (unless your organization uses it).
12. **SSH:** tick **Install OpenSSH server**. If your public key is on GitHub or Launchpad you can import it here; otherwise add it in section 3.2. Leave *Allow password authentication over SSH* on for now; it is turned off in section 3.2.
13. **Featured server snaps:** select **nothing**. In particular, **do not select `docker`** here: the snap version doesn't work with this setup. Docker is installed in section 4.
14. Wait for *Installation complete*, then **Reboot now**. Remove the ISO from the VM when asked.

**Check:** the VM boots to a `portal-01 login:` prompt, and from your machine `ssh portaladm@10.20.30.40` asks for the password.

---

## 3. Prepare the server

From here on, work over SSH from your machine. Commands that start with `sudo` ask for the `portaladm` password.

### 3.1 Updates and disk size

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot                       # if the upgrade installed a new kernel; reconnect afterwards
```

Check that `/` has the whole disk:

```bash
df -h /                           # Size should be close to the disk size
sudo vgs                          # VFree should be 0 (or close)
```

If `VFree` shows free space, give it to `/`:

```bash
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
df -h /
```

### 3.2 SSH: keys only

On **your machine**, copy your public key to the server:

```bash
ssh-copy-id portaladm@10.20.30.40
ssh portaladm@10.20.30.40         # must log in WITHOUT asking for the account password
```

Only when that works, on the **server**, turn off password logins and direct root logins:

```bash
sudo tee /etc/ssh/sshd_config.d/10-portal.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
sudo sshd -t && sudo systemctl restart ssh
```

**Check:** open a *second* terminal and log in again before closing the first one. If it fails, fix it from the first terminal.

### 3.3 Time zone and clock

The portal stores times in UTC and shows them in each user's browser time, so the server's time zone only affects logs and scheduled jobs.

```bash
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl                       # "System clock synchronized: yes"
```

If the clock is not synchronized because the VM can't reach a public time server, point it at the organization's:

```bash
sudo sed -i 's/^#\?NTP=.*/NTP=ntp.my-organization.com/' /etc/systemd/timesyncd.conf
sudo systemctl restart systemd-timesyncd
timedatectl
```

### 3.4 Automatic security updates

Ubuntu Server installs them by default. Confirm:

```bash
systemctl is-enabled unattended-upgrades       # enabled
```

Security updates install automatically; a reboot is sometimes needed (`/var/run/reboot-required` exists). Reboot at a quiet time: the portal starts by itself.

### 3.5 Firewall

Allow SSH only from the administrators' network, and the web ports from everywhere the users are:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.20.0.0/16 to any port 22 proto tcp     # the administrators' network
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

> Docker manages its own firewall rules, and ports published by containers are **not** filtered by `ufw`. The portal publishes only 80 and 443 (nginx), which are open anyway; the database and the API are not published. If you need to limit *who* reaches 443, do it in the network firewall, not with `ufw`.

### 3.6 Proxy (only if the VM has no direct internet access)

The installer set the proxy for `apt` only. Make it available to the shell too:

```bash
sudo tee -a /etc/environment >/dev/null <<'EOF'
http_proxy=http://proxy.my-organization.com:3128
https_proxy=http://proxy.my-organization.com:3128
no_proxy=localhost,127.0.0.1,.my-organization.com
EOF
```

Log out and in again. Docker needs its own proxy settings; they are in section 4.2.

---

## 4. Install Docker

Use Docker's own repository. The `docker.io` package in Ubuntu and the snap are older and are not what this guide was tested with.

### 4.1 Docker Engine and Compose

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Let `portaladm` use Docker without `sudo` (log out and in again afterwards):

```bash
sudo usermod -aG docker portaladm
```

> Membership of the `docker` group is equivalent to root on this server. Add only the administrators.

Limit the size of container logs, so they can't fill the disk:

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" }
}
EOF
sudo systemctl restart docker
```

### 4.2 Proxy for Docker (only if needed)

The Docker service downloads images; the builds download libraries. Both need the proxy:

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf >/dev/null <<'EOF'
[Service]
Environment="HTTP_PROXY=http://proxy.my-organization.com:3128"
Environment="HTTPS_PROXY=http://proxy.my-organization.com:3128"
Environment="NO_PROXY=localhost,127.0.0.1,.my-organization.com"
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker

mkdir -p ~/.docker
cat > ~/.docker/config.json <<'EOF'
{ "proxies": { "default": {
    "httpProxy": "http://proxy.my-organization.com:3128",
    "httpsProxy": "http://proxy.my-organization.com:3128",
    "noProxy": "localhost,127.0.0.1,db,api,web,.my-organization.com"
} } }
EOF
```

`db`, `api` and `web` are the containers' own names; they must never go through the proxy.

**Check** (after logging out and in again):

```bash
docker run --rm hello-world       # prints "Hello from Docker!"
docker compose version            # v2.x
```

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
- [ ] `ufw` allows 22 from administrators only, and 80/443.
- [ ] Docker comes from `download.docker.com`; `docker compose version` works; log size is limited.
- [ ] `.env.production` has real secrets, mode `600`, and they are in the password manager.
- [ ] The certificate has the portal's name in its SAN, the full chain, and its expiry date in the calendar.
- [ ] `dc ps` shows four services up; `/api/health` answers from the office and from the VPN, without browser warnings.
- [ ] The first admin password was changed; team accounts exist.
- [ ] A test email reached the defense team.
- [ ] The nightly backup runs, goes outside the VM, and a restore was tested.
- [ ] The passphrase, secrets and admin password are in the password manager.

Next: [RUNBOOK.md](RUNBOOK.md) for updates, everyday operations, certificate renewal and troubleshooting.
