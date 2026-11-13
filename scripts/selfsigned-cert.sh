#!/bin/sh
# Issues a self-signed certificate for the portal, for when the organization's PKI
# hasn't provided one (docs/INSTALL.md section 7.2).
#
#   sudo scripts/selfsigned-cert.sh portal.redteam.my-organization.com 10.20.30.40
#
# "Self-signed" here means signed by a small certificate authority of the portal's own,
# created on the first run in /root/portal-ca (PORTAL_CA_DIR): users trust its ca.crt
# once, and a renewed server certificate (run the script again, then dc restart nginx)
# needs nothing more from them. ca.key never leaves that folder.
#
# Writes certs/fullchain.pem (server + CA), certs/privkey.pem and certs/ca.crt (the file
# users import), owned by the owner of the portal folder.
set -eu

NAME="${1:-}"
IP="${2:-}"
if [ -z "$NAME" ]; then
  echo "usage: $0 <portal DNS name> [server IP address]" >&2
  exit 2
fi
PORTAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CA_DIR="${PORTAL_CA_DIR:-/root/portal-ca}"
CERT_DIR="${PORTAL_CERT_OUT:-$PORTAL_DIR/certs}"
DAYS="${CERT_DAYS:-825}"          # 825 days: the most Apple devices accept for TLS

umask 077
mkdir -p "$CA_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. The certificate authority, once (valid 10 years). Config files instead of -addext,
#    so it works with OpenSSL 1.1.1 (SLES 15) and 3.x alike.
if [ ! -f "$CA_DIR/ca.key" ]; then
  cat > "$TMP/ca.cnf" <<EOF
[req]
distinguished_name = dn
x509_extensions = v3_ca
prompt = no
[dn]
CN = Red Team Portal CA ($(hostname))
[v3_ca]
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
EOF
  openssl req -x509 -config "$TMP/ca.cnf" -newkey rsa:3072 -nodes -sha256 -days 3650 \
    -keyout "$CA_DIR/ca.key" -out "$CA_DIR/ca.crt" 2>/dev/null
  echo "New certificate authority: $CA_DIR/ca.crt"
fi

# 2. The server certificate, signed by it.
SAN="DNS:$NAME"
[ -n "$IP" ] && SAN="$SAN,IP:$IP"
cat > "$TMP/req.cnf" <<EOF
[req]
distinguished_name = dn
prompt = no
[dn]
CN = $NAME
EOF
cat > "$TMP/server.ext" <<EOF
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = $SAN
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid
EOF
openssl req -new -config "$TMP/req.cnf" -newkey rsa:3072 -nodes \
  -keyout "$TMP/privkey.pem" -out "$TMP/server.csr" 2>/dev/null
openssl x509 -req -in "$TMP/server.csr" -CA "$CA_DIR/ca.crt" -CAkey "$CA_DIR/ca.key" \
  -CAserial "$CA_DIR/ca.srl" -CAcreateserial -sha256 -days "$DAYS" \
  -extfile "$TMP/server.ext" -out "$TMP/server.crt" 2>/dev/null
openssl verify -CAfile "$CA_DIR/ca.crt" "$TMP/server.crt" >/dev/null

# 3. Into the portal, readable by the portal folder's owner (nginx reads them as root).
mkdir -p "$CERT_DIR"
cat "$TMP/server.crt" "$CA_DIR/ca.crt" > "$CERT_DIR/fullchain.pem"
cp "$TMP/privkey.pem" "$CERT_DIR/privkey.pem"
cp "$CA_DIR/ca.crt" "$CERT_DIR/ca.crt"
chmod 755 "$CERT_DIR"
chmod 644 "$CERT_DIR/fullchain.pem" "$CERT_DIR/ca.crt"
chmod 600 "$CERT_DIR/privkey.pem"
OWNER="$(stat -c %u:%g "$PORTAL_DIR")"
chown "$OWNER" "$CERT_DIR" "$CERT_DIR/fullchain.pem" "$CERT_DIR/privkey.pem" "$CERT_DIR/ca.crt" 2>/dev/null || true

echo "Server certificate: $CERT_DIR/fullchain.pem"
openssl x509 -in "$TMP/server.crt" -noout -subject -enddate
echo "Names: $SAN"
echo
echo "Users import $CERT_DIR/ca.crt once (INSTALL.md section 7.3). Its fingerprints, to compare:"
openssl x509 -in "$CA_DIR/ca.crt" -noout -fingerprint -sha1
openssl x509 -in "$CA_DIR/ca.crt" -noout -fingerprint -sha256
echo
echo "If the portal is running: dc restart nginx"
