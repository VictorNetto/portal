# SUSE Linux Enterprise Server 16 and 15 SP7: system and Docker

Sections 2 to 4 of the [installation guide](../INSTALL.md) for **SUSE Linux Enterprise Server (SLES)**, version **16** or **15 SP7**. Do [section 1](../INSTALL.md#1-before-you-start) first; when you finish here, continue with [section 5](../INSTALL.md#5-get-the-portal-code).

Examples use the values from section 1: server `portal-01` at `10.20.30.40`, administrator `portaladm`, administrators' network `10.20.0.0/16`.

## Which version

**Use SLES 16 if you can.** Both run the portal; the difference is in keeping Docker up to date:

| | SLES 16 | SLES 15 SP7 |
|---|---|---|
| Docker Engine and buildx | SUSE packages | SUSE packages (Containers Module) |
| Docker Compose | **SUSE package**: supported, updated with the system | Not packaged: downloaded from Docker and **updated by hand** |
| Container confinement | SELinux | AppArmor |
| Installer | Agama (new) | YaST |
| Future | Current release | SP7 is the last service pack of 15 |

Both were tested with this guide's Docker steps followed by the portal's sections 5 to 10: build, start, HTTPS, login, backup and restore (`scripts/install-test/`).

Most steps are the same on both. Where they differ, the step says **SLES 16** or **SLES 15**.

**You need** a registration code, or the address of the organization's RMT or SUSE Manager server (ask IT, section 1.2): without registration the server gets no updates.

---

## 2. Install the system

### 2.1 SLES 16

Use the SLES 16 installation image from the SUSE customer center, with the organization's account. Boot the VM from it and choose **Install SUSE Linux Enterprise Server 16**.

The installer (Agama) shows an **overview** with one section per topic; open each, then *Install*. Labels can differ slightly between 16.x releases.

1. **Product:** **SUSE Linux Enterprise Server 16**; accept the license.
2. **Localization:** language *English (US)* (recommended: log messages and online help are in English); keyboard: your layout (for example *Portuguese (Brazil)*); time zone *America/Sao_Paulo*.
3. **Network:** edit the wired connection → IPv4 **Manual**: address `10.20.30.40/24`, gateway `10.20.30.1`, the organization's DNS servers. (It can also be set after installation, below.)
4. **Registration:** the **registration code**, or the organization's RMT / SUSE Manager address (*custom registration server*). If the VM can't reach them without a proxy, register after installation (section 3.8).
5. **Storage:** the VM's disk, with **LVM**. Change the root file system (`/`) from Btrfs to **XFS** (the portal's database works better without copy-on-write and system snapshots), and remove a separate `/home` if one is proposed, so `/` gets the whole disk. Leave encryption off unless your policy requires it (an encrypted disk asks for a passphrase at every boot, so the server can't restart unattended).
6. **Software:** the default selection, with no desktop.
7. **Users:**
   - First user: full name `Portal Admin`, user name `portaladm`, a strong password, stored in the password manager.
   - Root: a **different** strong password, also stored. It is needed once, in section 3.1.
8. **Install**, then reboot. Remove the ISO from the VM.

If the network was not set in the installer, set it at the console with NetworkManager:

```bash
nmcli connection show                                   # the connection's name, for example "Wired connection 1"
sudo nmcli connection modify "Wired connection 1" ipv4.method manual \
  ipv4.addresses 10.20.30.40/24 ipv4.gateway 10.20.30.1 \
  ipv4.dns "10.20.0.53 10.20.0.54" ipv4.dns-search my-organization.com
sudo nmcli connection up "Wired connection 1"
sudo hostnamectl set-hostname portal-01
```

If SSH doesn't answer after the reboot, turn it on at the console: `sudo systemctl enable --now sshd` and `sudo firewall-cmd --add-service=ssh` (section 3.6 makes the firewall rules permanent).

### 2.2 SLES 15 SP7

Use the full image, `SLE-15-SP7-Full-x86_64-GM-Media1.iso`, from the SUSE customer center. Boot the VM from it and choose **Installation**.

The installer (YaST) is graphical; *Next* moves to the following screen.

1. **Language, Keyboard and Product Selection:** language *English (US)*; keyboard: your layout; product: **SUSE Linux Enterprise Server 15 SP7**.
2. **License Agreement:** accept.
3. **Network:** on the *Registration* screen, click **Network Configuration…** and set the static address before registering:
   - *Overview* → select the card → *Edit* → **Statically Assigned IP Address**: `10.20.30.40`, subnet mask `/24`, hostname `portal-01` → *Next*.
   - *Hostname/DNS*: static hostname `portal-01`; name servers: the organization's; domain search: `my-organization.com`.
   - *Routing*: default IPv4 gateway `10.20.30.1`.
   - *OK*.
4. **Registration:** either the organization's email and **registration code**, or **Register System via local RMT Server** with the address IT gave you. If the VM can reach neither without a proxy, choose **Skip Registration**: the full image has everything needed to install, and the server is registered in section 3.8.
5. **Extension and Module Selection:** keep **Basesystem** and **Server Applications** ticked, and tick **Containers Module** (Docker comes from it).
6. **Add-On Product:** none.
7. **System Role:** **Text Mode**.
8. **Suggested Partitioning:** **Guided Setup**:
   - Tick **Enable Logical Volume Management (LVM)**; leave encryption off unless your policy requires it.
   - Filesystem for the root partition: **XFS** (not the default Btrfs, as in 2.1).
   - Untick **Propose Separate Home Partition**, so `/` gets the rest of the disk.
   - Swap: keep the proposal.
   - Accept, and check the sizes on the summary. If `/` didn't get the whole disk, section 3.2 fixes it.
9. **Clock and Time Zone:** *Brazil*, *Sao Paulo* (or your region); keep *Hardware Clock Set to UTC*.
10. **Local User:** full name `Portal Admin`, username `portaladm`, a strong password. **Untick** *Use this password for system administrator*.
11. **Authentication for the System Administrator "root":** a different strong password. It is needed once, in section 3.1.
12. **Installation Settings** (summary), under *Security*: Firewall **enabled**; SSH service **enabled**; SSH port **open** (click *open* if it says *blocked*). Then **Install**. The VM restarts by itself; remove the ISO when it does.

**Check (both versions):** the VM boots to a `portal-01 login:` prompt, and from your machine `ssh portaladm@10.20.30.40` asks for the password.

---

## 3. Prepare the server

From here on, work over SSH from your machine.

If the VM has no direct internet access, do **3.1** and then **3.8 Proxy** first: everything else downloads packages.

### 3.1 The `portaladm` account and `sudo`

All administration is done from one personal account, `portaladm`, which may use `sudo`. The installer created the account in section 2, but on SLES it is not an administrator yet, and by default `sudo` asks for the **root** password. Put the account in the **`wheel`** group and let that group use `sudo` with its own password. Become root once:

```bash
su -                                                   # the root password from section 2
id portaladm                                           # "no such user"? create it first, below
groupadd -f -r wheel                                   # the administrators' group (does nothing if it exists)
usermod -aG wheel portaladm
printf '%s\n' 'Defaults:%wheel !targetpw' '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/50-wheel
chmod 440 /etc/sudoers.d/50-wheel
visudo -c -f /etc/sudoers.d/50-wheel                   # "parsed OK"
exit
```

**If the account doesn't exist** (the system was installed by someone else, for example from IT's template, or with another user name), create it as root before the `groupadd` line:

```bash
useradd -m -s /bin/bash -c "Portal Admin" portaladm    # -m creates /home/portaladm
passwd portaladm                                       # a strong password, stored in the password manager
```

If the root password is not yours, ask whoever has it to run these commands.

Then **log out and in again** as `portaladm`, so the new group applies.

**Check:** `id` lists `wheel`, and `sudo -k; sudo true` asks for **portaladm**'s password (`[sudo] password for portaladm:`), then returns without an error.

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

SUSE's own SSH configuration (`/etc/ssh/sshd_config` on 15, `/usr/etc/ssh/sshd_config` on 16) reads `/etc/ssh/sshd_config.d` first, and for each setting SSH keeps the first value it reads; on 15 that overrides its `PermitRootLogin yes`. The last command shows the values in effect.

**Check:** open a *second* terminal and log in again before closing the first one. If it fails, fix it from the first terminal.

### 3.4 Time zone and clock

The portal stores times in UTC and shows them in each user's browser time, so the server's time zone only affects logs and scheduled jobs:

```bash
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl                       # "System clock synchronized: yes"
```

If the clock is not synchronized because the VM can't reach a public time server, point it at the organization's. The file name replaces SUSE's public pool (on 15 it is that file; on 16 it overrides the one in `/usr/etc/chrony.d`):

```bash
echo 'server ntp.my-organization.com iburst' | sudo tee /etc/chrony.d/pool.conf
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

`firewalld` is on by default. Allow SSH only from the administrators' network, and the web ports from everywhere the users are:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.20.0.0/16" service name="ssh" accept'
sudo firewall-cmd --permanent --remove-service=ssh
sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all       # services: http https (dhcpv6-client); the rich rule for ssh
```

(`--remove-service` prints a warning if that service was not allowed; that's fine.) **Check** with a second SSH login, as in 3.3, before closing the first terminal.

> Docker manages its own firewall rules, and ports published by containers are **not** filtered by these rules. The portal publishes only 80 and 443 (nginx), which are open anyway; the database and the API are not published. If you need to limit *who* reaches 443, do it in the network firewall.

### 3.7 SELinux (16) or AppArmor (15)

Both confine containers, and both are on by default. **Leave them on.**

- **SLES 16:** `getenforce` says `Enforcing`. SUSE's Docker package turns on Docker's SELinux support (section 4.1), and `docker-compose.prod.yml` labels the two files nginx reads from the server's disk (its configuration and the certificate folder) with the `z` option.
- **SLES 15:** AppArmor; nothing to do.

### 3.8 Proxy (only if the VM has no direct internet access)

One file sets the proxy for `zypper`, registration and the shell:

```bash
sudo sed -i -e 's|^PROXY_ENABLED=.*|PROXY_ENABLED="yes"|' \
            -e 's|^HTTP_PROXY=.*|HTTP_PROXY="http://proxy.my-organization.com:3128"|' \
            -e 's|^HTTPS_PROXY=.*|HTTPS_PROXY="http://proxy.my-organization.com:3128"|' \
            -e 's|^NO_PROXY=.*|NO_PROXY="localhost, 127.0.0.1, .my-organization.com"|' /etc/sysconfig/proxy
```

Log out and in again. If you skipped registration during installation, register now, then run the updates of section 3.2:

```bash
sudo SUSEConnect -r <registration code>              # or: sudo SUSEConnect --url https://rmt.my-organization.com
```

Docker needs its own proxy settings; they are in section 4.3.

---

## 4. Install Docker

### 4.1 Docker Engine (and Compose on 16)

**SLES 16:** Docker, buildx and Compose are all SUSE packages:

```bash
sudo zypper -n install docker docker-buildx docker-compose
```

**SLES 15:** Docker comes from the Containers Module. If you didn't tick it in the installer, add it first; Compose is installed in 4.2:

```bash
sudo SUSEConnect -p sle-module-containers/15.7/x86_64   # only if it is missing
sudo zypper -n install docker docker-buildx
```

Then, on both:

```bash
sudo systemctl enable --now docker
sudo usermod -aG docker portaladm                         # log out and in again afterwards
```

> Membership of the `docker` group is equivalent to root on this server. Add only the administrators.

**Leave `/etc/docker/daemon.json` as SUSE ships it.** It already limits the size of container logs (5 files of 10 MB per container) and turns on Docker's SELinux support, which matters on 16:

```bash
sudo cat /etc/docker/daemon.json          # "log-opts": max-size 10m, max-file 5; "selinux-enabled": true
docker info --format '{{.SecurityOptions}}'   # SLES 16: includes name=selinux; SLES 15: name=apparmor
```

### 4.2 Compose plugin (SLES 15 only)

SLES 15 has no Compose package. Download the plugin from Docker's releases, check it, and install it where Docker looks for plugins. Use the latest version listed at [github.com/docker/compose/releases](https://github.com/docker/compose/releases):

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
docker compose version            # 2.x on SLES 16 (SUSE's package), v5.x on SLES 15 (Docker's)
docker buildx version             # the builds use it
```

---

Next: [section 5, Get the portal code](../INSTALL.md#5-get-the-portal-code).
