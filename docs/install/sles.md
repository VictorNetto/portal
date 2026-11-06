# SUSE Linux Enterprise Server 15 SP7: system and Docker

Sections 2 to 4 of the [installation guide](../INSTALL.md) for **SUSE Linux Enterprise Server (SLES) 15 SP7**. Do [section 1](../INSTALL.md#1-before-you-start) first; when you finish here, continue with [section 5](../INSTALL.md#5-get-the-portal-code).

Examples use the values from section 1: server `portal-01` at `10.20.30.40`, administrator `portaladm`, administrators' network `10.20.0.0/16`.

Docker comes from SUSE's **Containers Module**, so it is covered by the SLES subscription and updated with the system. That module has no Compose plugin, so Compose is installed from Docker's releases and updated by hand (section 4.2).

**You need** a registration code, or the address of the organization's RMT or SUSE Manager server (ask IT, section 1.2): without registration the server gets no updates and can't add the Containers Module.

> **SLES 16** is a different installer and system (SELinux instead of AppArmor, NetworkManager, other module names). This guide is for SLES 15 SP7; on SLES 16, check the steps with IT first.

---

## 2. Install SLES 15 SP7

Use the full image, `SLE-15-SP7-Full-x86_64-GM-Media1.iso`, from the SUSE customer center with the organization's account. Boot the VM from it and choose **Installation**.

The installer (YaST) is graphical; *Next* moves to the following screen.

1. **Language, Keyboard and Product Selection:** language *English (US)* (recommended: log messages and online help are in English); keyboard: your layout (for example *Portuguese (Brazil)*); product: **SUSE Linux Enterprise Server 15 SP7**.
2. **License Agreement:** accept.
3. **Network:** on the *Registration* screen, click **Network Configuration…** and set the static address before registering:
   - *Overview* → select the card → *Edit* → **Statically Assigned IP Address**: `10.20.30.40`, subnet mask `/24`, hostname `portal-01` → *Next*.
   - *Hostname/DNS*: static hostname `portal-01`; name servers: the organization's; domain search: `my-organization.com`.
   - *Routing*: default IPv4 gateway `10.20.30.1`.
   - *OK*.
4. **Registration:** either the organization's email and **registration code**, or **Register System via local RMT Server** with the address IT gave you. If the VM can reach neither without a proxy, choose **Skip Registration**: the full image has everything needed to install, and the server is registered in section 3.8, after the proxy is set.
5. **Extension and Module Selection:** keep **Basesystem** and **Server Applications** ticked, and tick **Containers Module**.
6. **Add-On Product:** none.
7. **System Role:** **Text Mode**.
8. **Suggested Partitioning:** **Guided Setup**:
   - Tick **Enable Logical Volume Management (LVM)**; leave encryption off unless your policy requires it (an encrypted disk asks for a passphrase at every boot, so the server can't restart unattended).
   - Filesystem for the root partition: **XFS**. The default, Btrfs, keeps snapshots of the system, and the portal's database works better without copy-on-write.
   - Untick **Propose Separate Home Partition**, so `/` gets the rest of the disk.
   - Swap: keep the proposal.
   - Accept, and check the sizes on the summary. If `/` didn't get the whole disk, section 3.2 fixes it.
9. **Clock and Time Zone:** *Brazil*, *Sao Paulo* (or your region); keep *Hardware Clock Set to UTC*. Under *Other Settings*, choose **Synchronize with NTP Server** and enter the organization's NTP server if the VM can't reach a public one; tick *Save NTP Configuration*.
10. **Local User:**
    - User's full name: `Portal Admin`
    - Username: `portaladm`
    - Password: a strong one, stored in the password manager.
    - **Untick** *Use this password for system administrator*, so `root` gets its own password.
11. **Authentication for the System Administrator "root":** a different strong password, stored in the password manager. It is needed once, in section 3.1.
12. **Installation Settings** (summary). Check under *Security*:
    - Firewall **enabled**.
    - SSH service **enabled**, SSH port **open** (click *open* if it says *blocked*).

    Then **Install** → *Install*. The VM restarts by itself; remove the ISO when it does.

**Check:** the VM boots to a `portal-01 login:` prompt, and from your machine `ssh portaladm@10.20.30.40` asks for the password.

---

## 3. Prepare the server

From here on, work over SSH from your machine.

If the VM has no direct internet access, do **3.1** and then **3.8 Proxy** first: everything else downloads packages.

### 3.1 `sudo` with your own password

By default, `sudo` on SLES asks for the **root** password. Make it ask for `portaladm`'s, like the rest of this guide expects. Become root once:

```bash
su -                                                   # the root password from section 2
printf '%s\n' 'Defaults:portaladm !targetpw' 'portaladm ALL=(ALL:ALL) ALL' > /etc/sudoers.d/50-portaladm
chmod 440 /etc/sudoers.d/50-portaladm
visudo -c                                              # "parsed OK" for every file
exit
```

**Check:** `sudo -k; sudo true` asks for **portaladm**'s password (`[sudo] password for portaladm:`).

### 3.2 Updates, tools and disk size

```bash
sudo zypper refresh
sudo zypper -n patch              # run it again if it says the package manager itself was updated
sudo zypper -n install git-core
sudo reboot                       # if the patches need it; reconnect afterwards
```

Check that `/` has the whole disk:

```bash
df -h /                           # Size should be close to the disk size
sudo vgs                          # VFree should be 0 (or close)
```

If `VFree` shows free space, give it to `/`:

```bash
sudo lvextend -r -l +100%FREE "$(findmnt -n -o SOURCE /)"
df -h /
```

### 3.3 SSH: keys only

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
sudo sshd -t && sudo systemctl restart sshd
sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin)'   # both "no"
```

SLES's own `/etc/ssh/sshd_config` says `PermitRootLogin yes`, but it reads `sshd_config.d` first, and for each setting SSH keeps the first value it reads. The last command shows the values in effect.

**Check:** open a *second* terminal and log in again before closing the first one. If it fails, fix it from the first terminal.

### 3.4 Time zone and clock

The portal stores times in UTC and shows them in each user's browser time, so the server's time zone only affects logs and scheduled jobs. If you set them in the installer, just check:

```bash
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl                       # "System clock synchronized: yes"
```

If the clock is not synchronized because the VM can't reach a public time server, point it at the organization's:

```bash
sudo mv /etc/chrony.d/pool.conf /etc/chrony.d/pool.conf.off
echo 'server ntp.my-organization.com iburst' | sudo tee /etc/chrony.d/portal.conf
sudo systemctl enable --now chronyd && sudo systemctl restart chronyd
chronyc sources                   # the organization's server, marked with ^*
```

### 3.5 Automatic security updates

If the organization patches its SLES servers centrally (SUSE Manager, or another tool), register this server there and skip this section.

Otherwise, install security patches every night with a small scheduled job:

```bash
sudo tee /etc/systemd/system/security-patches.service >/dev/null <<'EOF'
[Unit]
Description=Install security patches
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/zypper --non-interactive patch --category security --auto-agree-with-licenses
# 102: a reboot is needed; 103: zypper updated itself and runs again next time.
SuccessExitStatus=102 103
EOF
sudo tee /etc/systemd/system/security-patches.timer >/dev/null <<'EOF'
[Unit]
Description=Install security patches every night

[Timer]
OnCalendar=*-*-* 04:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now security-patches.timer
systemctl list-timers security-patches.timer       # shows the next run
```

`sudo zypper needs-rebooting` tells whether a reboot is needed; reboot at a quiet time: the portal starts by itself.

### 3.6 Firewall

`firewalld` is on (section 2). Allow SSH only from the administrators' network, and the web ports from everywhere the users are:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.20.0.0/16" service name="ssh" accept'
sudo firewall-cmd --permanent --remove-service=ssh
sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all       # services: http https (dhcpv6-client); the rich rule for ssh
```

**Check** with a second SSH login, as in 3.3, before closing the first terminal.

> Docker manages its own firewall rules, and ports published by containers are **not** filtered by these rules. The portal publishes only 80 and 443 (nginx), which are open anyway; the database and the API are not published. If you need to limit *who* reaches 443, do it in the network firewall.

### 3.7 AppArmor

SLES 15 protects containers with AppArmor, on by default. Nothing to do; leave it on.

### 3.8 Proxy (only if the VM has no direct internet access)

On SLES one file sets the proxy for `zypper`, registration and the shell:

```bash
sudo sed -i -e 's|^PROXY_ENABLED=.*|PROXY_ENABLED="yes"|' \
            -e 's|^HTTP_PROXY=.*|HTTP_PROXY="http://proxy.my-organization.com:3128"|' \
            -e 's|^HTTPS_PROXY=.*|HTTPS_PROXY="http://proxy.my-organization.com:3128"|' \
            -e 's|^NO_PROXY=.*|NO_PROXY="localhost, 127.0.0.1, .my-organization.com"|' /etc/sysconfig/proxy
```

(`sudo yast proxy` does the same with menus.) Log out and in again. If you skipped registration during installation, register now, then add the Containers Module (section 4.1) and run the updates of section 3.2:

```bash
sudo SUSEConnect -r <registration code>              # or: sudo SUSEConnect --url https://rmt.my-organization.com
```

Docker needs its own proxy settings; they are in section 4.3.

---

## 4. Install Docker

### 4.1 Docker Engine

The Docker package comes from the Containers Module. If you didn't tick it in the installer, add it first:

```bash
sudo SUSEConnect -p sle-module-containers/15.7/x86_64   # only if it is missing
sudo SUSEConnect --status-text | grep -A2 -i containers  # Registered
```

```bash
sudo zypper -n install docker docker-buildx
sudo systemctl enable --now docker
```

Let `portaladm` use Docker without `sudo` (log out and in again afterwards):

```bash
sudo usermod -aG docker portaladm
```

> Membership of the `docker` group is equivalent to root on this server. Add only the administrators.

Limit the size of container logs, so they can't fill the disk. The package may already have created `/etc/docker/daemon.json`; look at it first (`sudo cat /etc/docker/daemon.json`) and keep any other setting it has:

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" }
}
EOF
sudo systemctl restart docker
```

### 4.2 Compose plugin

Download the plugin from Docker's releases, check it, and install it where Docker looks for plugins. Use the latest version listed at [github.com/docker/compose/releases](https://github.com/docker/compose/releases):

```bash
COMPOSE_VERSION=v5.7.0
cd /tmp
curl -fLO "https://github.com/docker/compose/releases/download/$COMPOSE_VERSION/docker-compose-linux-x86_64"
curl -fLO "https://github.com/docker/compose/releases/download/$COMPOSE_VERSION/docker-compose-linux-x86_64.sha256"
sha256sum -c docker-compose-linux-x86_64.sha256      # docker-compose-linux-x86_64: OK
sudo install -D -m 0755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
rm docker-compose-linux-x86_64*
cd ~
```

`zypper` does not update this file. Repeat these commands with the new version a few times a year, or when Docker publishes a security fix for Compose.

### 4.3 Proxy for Docker (only if needed)

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
docker buildx version             # the builds use it
```

---

Next: [section 5, Get the portal code](../INSTALL.md#5-get-the-portal-code).
