#!/usr/bin/env bash
# Install test on SUSE Linux Enterprise Server: follows docs/install/sles.md (Docker from
# SUSE's packages) and INSTALL.md (configure, build, start, check, back up, restore) inside
# a privileged SLES container, one per version, in parallel.
#
#   scripts/install-test/run.sh            # SLES 15 SP7 and 16
#   scripts/install-test/run.sh 16         # one version
#
# Tests the committed code (git archive HEAD). Needs Docker and about 3 GB per version;
# each version keeps a Docker volume (portal-install-test-slesNN) so reruns are faster.
# Remove them with: docker volume rm portal-install-test-sles15 portal-install-test-sles16
#
# What it does NOT cover: the installer screens, systemd, the firewall, and SELinux or
# AppArmor enforcement (the container runs on this machine's kernel, not SUSE's).
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSIONS=("${@:-15 16}")
read -r -a VERSIONS <<< "${VERSIONS[*]}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git archive --format=tar -o "$WORK/portal.tar" HEAD
cp scripts/install-test/inside.sh "$WORK/inside.sh"
hostpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

declare -A IMAGE=([15]=registry.suse.com/bci/bci-base:15.7 [16]=registry.suse.com/bci/bci-base:16.0)
for v in "${VERSIONS[@]}"; do
  [ -n "${IMAGE[$v]:-}" ] || { echo "unknown version: $v (use 15 or 16)" >&2; exit 2; }
  echo "SLES $v: running (log: $WORK/sles$v.log) ..."
  ( MSYS_NO_PATHCONV=1 docker run --rm --privileged --name "portal-install-test-sles$v" \
      -v "portal-install-test-sles$v:/var/lib/docker" -v "$(hostpath "$WORK"):/work:ro" \
      "${IMAGE[$v]}" bash /work/inside.sh "$v" > "$WORK/sles$v.log" 2>&1
    echo "exit=$?" >> "$WORK/sles$v.log" ) &
done
wait

status=0
for v in "${VERSIONS[@]}"; do
  echo
  echo "################ SLES $v"
  grep -v -E '^\s*$|Downloading|Extracting|Pull|Waiting|Verifying|Download complete|Already exists|^ [0-9a-f]{12} | (Container|Network|Volume) |alembic.runtime' "$WORK/sles$v.log"
  grep -q '^exit=0$' "$WORK/sles$v.log" || status=1
done
exit $status
