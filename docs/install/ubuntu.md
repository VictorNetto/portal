# Ubuntu Server 24.04 LTS: system and Docker

Sections 2 to 4 of the [installation guide](../INSTALL.md) for **Ubuntu Server 24.04 LTS**. Do [section 1](../INSTALL.md#1-before-you-start) first; when you finish here, continue with [section 5](../INSTALL.md#5-get-the-portal-code).

Examples use the values from section 1: server `portal-01` at `10.20.30.40`, administrator `portaladm`, administrators' network `10.20.0.0/16`.

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

   On the summary screen, **check the size of `ubuntu-lv` (mounted at `/`)**: Ubuntu often uses only part of the disk. If it is smaller than the disk, select it → *Edit* → set the size to the maximum shown → *Save*. (If you miss this, it can be fixed later, section 3.1 below.)
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
docker compose version            # v2 or later
```

---

Next: [section 5, Get the portal code](../INSTALL.md#5-get-the-portal-code).
