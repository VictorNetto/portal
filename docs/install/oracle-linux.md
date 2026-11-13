# Oracle Linux 9: system and Docker

Sections 2 to 4 of the [installation guide](../INSTALL.md) for **Oracle Linux 9**. Do [section 1](../INSTALL.md#1-before-you-start) first; when you finish here, continue with [section 5](../INSTALL.md#5-get-the-portal-code).

Examples use the values from section 1: server `portal-01` at `10.20.30.40`, administrator `portaladm`, administrators' network `10.20.0.0/16`.

Oracle Linux is free to use and to update (packages come from `yum.oracle.com`); support is a separate, optional contract. Docker is installed from Docker's own repository for Red Hat Enterprise Linux, with which Oracle Linux is compatible.

---

## 2. Install Oracle Linux 9

Use the full DVD image, `OracleLinux-R9-Ux-x86_64-dvd.iso`, from [yum.oracle.com/oracle-linux-isos.html](https://yum.oracle.com/oracle-linux-isos.html) (the latest update, *U*). Boot the VM from it and choose **Install Oracle Linux 9**.

The installer is graphical. It opens on a language screen, then on the **Installation Summary**, a page of items you open one at a time, in any order; *Begin Installation* stays disabled until every item marked in red is done.

1. **Language:** English (United States) (recommended: log messages and online help are in English).
2. **Keyboard:** add your layout (for example *Portuguese (Brazil)*) and move it to the top.
3. **Network & Host Name:**
   - Host Name: `portal-01` → *Apply*.
   - Select the network card → *Configure…* → **IPv4 Settings**: Method **Manual**; *Add* the address `10.20.30.40`, netmask `24`, gateway `10.20.30.1`; DNS servers: the organization's, separated by commas; Search domains: `my-organization.com`. **General** tab: tick *Connect automatically with priority*. *Save*.
   - Switch the card **On** and check that it shows the address.
4. **Time & Date:** Region *America*, City *Sao Paulo*. Turn on **Network Time**; with the gear button, add the organization's NTP server if the VM can't reach a public one.
5. **Software Selection:** **Minimal Install**, with no additional software. Docker and the few tools needed are installed later.
6. **Installation Destination:** select the disk, choose **Custom** under *Storage Configuration*, then *Done*. On the next screen:
   - Partitioning scheme: **LVM**. Click *Click here to create them automatically*.
   - The automatic layout creates a large `/home`, which the portal doesn't use. Select **`/home`** and remove it with **−**.
   - Select **`/`**, type `1000 GiB` in *Desired Capacity* (the installer reduces it to all the space left) → *Update Settings*.
   - *Done* → *Accept Changes*.

   Leave encryption off unless your policy requires it (an encrypted disk asks for a passphrase at every boot, so the server can't restart unattended).
7. **KDUMP:** may be turned off; it reserves memory for crash dumps.
8. **Security Profile:** none, unless your policy requires one.
9. **Root Password:** tick **Lock root account**. Administration is done with `sudo` from your own account.
10. **User Creation:**
    - Full name: `Portal Admin`
    - User name: `portaladm`
    - Tick **Make this user administrator** (it joins the `wheel` group, which may use `sudo`).
    - Password: a strong one, stored in the password manager.
11. **Begin Installation**, then **Reboot System**. Remove the ISO from the VM.

The default kernel is Oracle's *Unbreakable Enterprise Kernel* (UEK); keep it.

**Check:** the VM boots to a `portal-01 login:` prompt, and from your machine `ssh portaladm@10.20.30.40` asks for the password.

---

## 3. Prepare the server

From here on, work over SSH from your machine. Commands that start with `sudo` ask for the `portaladm` password.

If the VM has no direct internet access, do **3.8 Proxy** first: everything below downloads packages.

### 3.1 The `portaladm` account and `sudo`

All administration is done from one personal account, `portaladm`, which may use `sudo` because it is in the **`wheel`** group. The installer created it in section 2 and put it there (*Make this user administrator*). Check:

```bash
id portaladm                      # the groups must include "wheel"
```

**If the account doesn't exist, or `wheel` is missing** (for example, the system was installed by someone else, from IT's template or with another user name), fix it from an account that already has `sudo`, or as root at the console:

```bash
sudo useradd -m -s /bin/bash -c "Portal Admin" portaladm   # only if it doesn't exist; -m creates /home/portaladm
sudo passwd portaladm                                      # only if just created: a strong password, stored in the password manager
sudo usermod -aG wheel portaladm                         # the "wheel" group may run any command with sudo, with portaladm's own password
```

Then **log out and in again** as `portaladm` (`ssh portaladm@10.20.30.40`), so the new group applies. Use only this account from here on.

**Check:** `id` lists `wheel`, and `sudo -k; sudo true` asks for **portaladm**'s password (`[sudo] password for portaladm:`), then returns without an error.

### 3.2 Updates, tools and disk size

```bash
sudo dnf -y upgrade
sudo dnf -y install git           # not part of the minimal installation
sudo reboot                       # if the upgrade installed a new kernel; reconnect afterwards
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

The file name starts with `10-` so it is read before the system's own `50-redhat.conf`: for each setting, SSH keeps the first value it reads.

**Check:** open a *second* terminal and log in again before closing the first one. If it fails, fix it from the first terminal.

### 3.4 Time zone and clock

The portal stores times in UTC and shows them in each user's browser time, so the server's time zone only affects logs and scheduled jobs. If you set them in the installer, just check:

```bash
sudo timedatectl set-timezone America/Sao_Paulo
timedatectl                       # "System clock synchronized: yes"
```

If the clock is not synchronized because the VM can't reach a public time server, point it at the organization's:

```bash
sudo sed -i 's/^pool .*/server ntp.my-organization.com iburst/' /etc/chrony.conf
sudo systemctl restart chronyd
chronyc sources                   # the organization's server, marked with ^*
```

### 3.5 Automatic security updates

```bash
sudo dnf -y install dnf-automatic
sudo sed -i -e 's/^upgrade_type = .*/upgrade_type = security/' \
            -e 's/^apply_updates = .*/apply_updates = yes/' /etc/dnf/automatic.conf
sudo systemctl enable --now dnf-automatic.timer
systemctl list-timers dnf-automatic.timer          # shows the next run
```

Security updates now install every day. `sudo dnf needs-restarting -r` tells whether a reboot is needed; reboot at a quiet time: the portal starts by itself.

### 3.6 Firewall

`firewalld` is on by default and lets SSH in from anywhere. Allow SSH only from the administrators' network, and the web ports from everywhere the users are:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.20.0.0/16" service name="ssh" accept'
sudo firewall-cmd --permanent --remove-service=ssh
sudo firewall-cmd --permanent --remove-service=cockpit
sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all       # services: http https (dhcpv6-client); the rich rule for ssh
```

(`--remove-service` prints a warning if that service was not allowed; that's fine.) **Check** with a second SSH login, as in 3.3, before closing the first terminal.

> Docker manages its own firewall rules, and ports published by containers are **not** filtered by these rules. The portal publishes only 80 and 443 (nginx), which are open anyway; the database and the API are not published. If you need to limit *who* reaches 443, do it in the network firewall.

### 3.7 SELinux

SELinux is on (*Enforcing*) by default. **Keep it on.** The portal's containers work with it; section 4.1 turns on Docker's SELinux support.

```bash
getenforce                         # Enforcing
```

### 3.8 Proxy (only if the VM has no direct internet access)

For `dnf`:

```bash
echo 'proxy=http://proxy.my-organization.com:3128' | sudo tee -a /etc/dnf/dnf.conf
```

For the shell (`curl`, `git`):

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

Use Docker's own repository for Red Hat Enterprise Linux. Oracle Linux offers *Podman* instead of Docker, but the portal's commands and scripts use `docker compose`.

### 4.1 Docker Engine and Compose

Remove Podman and its tools if they are installed (they conflict with Docker's packages; on a minimal installation there is usually nothing to remove):

```bash
sudo dnf -y remove podman buildah runc
```

Add Docker's repository and install:

```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

The first install imports Docker's signing key and prints its fingerprint. It must be `060A 61C5 1B55 8A7F 742B 77AA C52F EB6B 621E 9F35`.

Let `portaladm` use Docker without `sudo` (log out and in again afterwards):

```bash
sudo usermod -aG docker portaladm
```

> Membership of the `docker` group is equivalent to root on this server. Add only the administrators.

Turn on Docker's SELinux support, and limit the size of container logs so they can't fill the disk:

```bash
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "selinux-enabled": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" }
}
EOF
sudo systemctl restart docker
docker info --format '{{.SecurityOptions}}'      # includes name=selinux
```

With SELinux support on, each container is confined to its own files. The two files the web server reads from the server's disk (its configuration and the certificate folder) are labelled for it automatically: `docker-compose.prod.yml` mounts them with the `z` option.

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

Docker's packages are updated with the rest of the system (`dnf`); `dnf-automatic` installs only the security ones.

---

Next: [section 5, Get the portal code](../INSTALL.md#5-get-the-portal-code).
