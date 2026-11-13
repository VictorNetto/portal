#!/bin/bash
# Runs INSIDE a SLES container (see run.sh): Docker from SUSE's own packages, as in
# docs/install/sles.md sections 3.1 and 4, then the portal as in INSTALL.md sections 6-10
# (with the self-signed certificate of section 7.2).
set -euo pipefail
VER="$1"                          # 15 or 16
step() { echo; echo "=== [$VER] $*"; }
T0=$(date +%s)

step "System"
grep PRETTY_NAME /etc/os-release

step "The portaladm account and sudo (sles.md section 3.1)"
for try in 1 2 3 4; do zypper -q -n install --no-recommends sudo shadow >/dev/null && break; echo "zypper failed (mirror), retry $try"; sleep 5; done
id portaladm 2>/dev/null || useradd -m -s /bin/bash -c "Portal Admin" portaladm
echo 'portaladm:Admin-Pass-123' | chpasswd
groupadd -f -r wheel
usermod -aG wheel portaladm
printf '%s
' 'Defaults:%wheel !targetpw' '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/50-wheel
chmod 440 /etc/sudoers.d/50-wheel
visudo -c
id portaladm | grep -q '(wheel)' && echo "portaladm is in wheel"
# With SUSE's "Defaults targetpw" still in effect, this would need root's password.
su - portaladm -c "echo Admin-Pass-123 | sudo -S -k -p '' id -un" | grep -qx root && echo "sudo with portaladm's own password: ok"

step "Docker from SUSE packages"
PKGS="docker docker-buildx curl openssl tar gzip iptables sudo shadow"
[ "$VER" = 16 ] && PKGS="$PKGS docker-compose"
for try in 1 2 3 4; do zypper -q -n --gpg-auto-import-keys install --no-recommends $PKGS >/dev/null && break; echo "zypper failed (mirror), retry $try"; sleep 5; done
rpm -q docker docker-buildx $([ "$VER" = 16 ] && echo docker-compose)
echo "--- SUSE's /etc/docker/daemon.json:"; cat /etc/docker/daemon.json 2>/dev/null || echo "(none)"

if [ "$VER" = 15 ]; then
  step "Compose plugin from Docker's releases (SLES 15 has no package)"
  cd /tmp
  curl -fsSLO https://github.com/docker/compose/releases/download/v5.7.0/docker-compose-linux-x86_64
  curl -fsSLO https://github.com/docker/compose/releases/download/v5.7.0/docker-compose-linux-x86_64.sha256
  sha256sum -c docker-compose-linux-x86_64.sha256
  install -D -m 0755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
  cd /
fi

step "Start dockerd (no systemd in a container; SUSE's daemon.json kept, as the guide says)"
dockerd >/var/log/dockerd.log 2>&1 &
for i in $(seq 60); do docker info >/dev/null 2>&1 && break; sleep 1; done
docker version --format 'engine {{.Server.Version}}'
docker compose version
docker buildx version
docker run --rm hello-world | grep 'Hello from Docker'

step "Portal code and configuration"
mkdir -p /opt/portal && tar -xf /work/portal.tar -C /opt/portal && cd /opt/portal
cp .env.production.example .env.production && chmod 600 .env.production
DBPW=$(openssl rand -hex 24); JWT=$(openssl rand -hex 32)
sed -i -e "s/^PORTAL_SERVER_NAME=.*/PORTAL_SERVER_NAME=portal.test/" \
       -e "s/CHANGE-ME-long-random/$DBPW/g" \
       -e "s/^JWT_SECRET=.*/JWT_SECRET=$JWT/" \
       -e "s/^FIRST_ADMIN_PASSWORD=.*/FIRST_ADMIN_PASSWORD=First-Admin-Pass-123/" \
       -e "s/^DISPATCH_TRANSPORT=.*/DISPATCH_TRANSPORT=stub/" .env.production
chown -R portaladm: /opt/portal

step "Self-signed certificate (INSTALL.md section 7.2)"
scripts/selfsigned-cert.sh portal.test 127.0.0.1
ls -l certs /root/portal-ca
stat -c '%U %a %n' certs/*
openssl verify -CAfile certs/ca.crt certs/fullchain.pem
scripts/selfsigned-cert.sh portal.test 127.0.0.1 | grep -q 'New certificate authority' && { echo "a second run must reuse the CA" >&2; exit 1; }
openssl verify -CAfile /root/portal-ca/ca.crt certs/fullchain.pem >/dev/null && echo "renewal kept the same CA"

step "Build and start (INSTALL.md section 8)"
export PORTAL_ENV_FILE=.env.production
dc() { docker compose -f docker-compose.prod.yml --env-file .env.production "$@"; }
B0=$(date +%s)
docker compose --progress=quiet -f docker-compose.prod.yml --env-file .env.production build
echo "build took $(( $(date +%s) - B0 ))s"
dc down -v --remove-orphans >/dev/null 2>&1 || true   # leftovers of an earlier run
dc up -d db
dc run --rm api alembic upgrade head 2>&1 | tail -4
dc up -d
for i in $(seq 90); do
  curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 https://portal.test/api/health 2>/dev/null && break; sleep 2
done
echo; dc ps --format '{{.Service}}: {{.Status}}'

step "Checks (INSTALL.md section 9)"
curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 https://portal.test/api/health; echo
curl -fsS --cacert certs/ca.crt https://127.0.0.1/api/health >/dev/null && echo "by IP address (in the SAN): ok"
curl -s -o /dev/null -w 'http -> %{http_code} %{redirect_url}\n' --resolve portal.test:80:127.0.0.1 http://portal.test/
curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 https://portal.test/ | grep -o '<title>[^<]*</title>'
curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"First-Admin-Pass-123"}' https://portal.test/api/auth/login \
  | grep -o '"access_token"' && echo "admin login: ok"

step "Backup and restore (INSTALL.md section 10)"
export BACKUP_PASSPHRASE=$(openssl rand -hex 16)
scripts/backup.sh /tmp/bk 2>&1 | tail -2
ls -lh /tmp/bk
scripts/restore.sh "$(ls /tmp/bk/*.enc | head -1)" --yes 2>&1 | tail -2
R0=$(date +%s)
for i in $(seq 60); do curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 https://portal.test/api/health >/dev/null 2>&1 && break; sleep 1; done
curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 https://portal.test/api/health; echo " (answered $(( $(date +%s) - R0 ))s after the restore)"
curl -fsS --cacert certs/ca.crt --resolve portal.test:443:127.0.0.1 -H 'Content-Type: application/json'   -d '{"username":"admin","password":"First-Admin-Pass-123"}' https://portal.test/api/auth/login | grep -q access_token && echo "admin login after restore: ok"

step "Disk used by Docker"
du -sh /var/lib/docker 2>/dev/null | cut -f1

step "RESULT: PASSED in $(( $(date +%s) - T0 ))s"
