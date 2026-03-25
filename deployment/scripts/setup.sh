#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-time server bootstrap script
#
# Run this ONCE on a fresh Ubuntu 22.04 server BEFORE running deploy.sh.
# Usage:
#   ssh ubuntu@<SERVER_IP>
#   wget https://raw.githubusercontent.com/<YOU>/Discord_bot_AI/main/deployment/scripts/setup.sh
#   chmod +x setup.sh && sudo ./setup.sh
# =============================================================================
set -euo pipefail

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

[[ $(id -u) -eq 0 ]] || error "Run as root: sudo ./setup.sh"

info "=== Discord Study Bot — Server Setup ==="
info "Date: $(date)"
info "Hostname: $(hostname)"

# ── System packages ───────────────────────────────────────────────────────────
info "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

info "Installing system dependencies..."
apt-get install -y -qq \
  build-essential git curl wget unzip \
  python3.11 python3.11-venv python3.11-dev python3-pip \
  ffmpeg libopus0 libopus-dev \
  libffi-dev libssl-dev libsqlite3-dev \
  htop nano vim ufw logrotate \
  pkg-config

# ── Python 3.11 as default python3 ───────────────────────────────────────────
info "Setting Python 3.11 as default python3..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --set python3 /usr/bin/python3.11
python3 --version

# ── Application user ──────────────────────────────────────────────────────────
info "Creating botuser system account..."
if id "botuser" &>/dev/null; then
  warn "botuser already exists, skipping creation"
else
  useradd --system --create-home --shell /bin/bash botuser
fi

# ── Directory structure ───────────────────────────────────────────────────────
info "Creating directory structure..."
mkdir -p /opt/discord-bot
mkdir -p /opt/botdata/chromadb
mkdir -p /opt/botdata/uploads
mkdir -p /var/log/discord-bot

chown -R botuser:botuser /opt/discord-bot
chown -R botuser:botuser /opt/botdata
chown -R botuser:botuser /var/log/discord-bot

# ── Mount persistent block volume (ChromaDB data) ────────────────────────────
# The OCI block volume is attached as /dev/sdb or /dev/oracleoci/oraclevdb
info "Checking for data volume..."
DATA_DEV=""
for dev in /dev/sdb /dev/oracleoci/oraclevdb /dev/vdb; do
  if [[ -b "$dev" ]]; then
    DATA_DEV="$dev"
    break
  fi
done

if [[ -n "$DATA_DEV" ]]; then
  info "Found data volume at $DATA_DEV"
  # Format only if no filesystem present
  if ! blkid "$DATA_DEV" &>/dev/null; then
    info "Formatting $DATA_DEV as ext4..."
    mkfs.ext4 -L botdata "$DATA_DEV"
  fi
  # Add to fstab if not already there
  if ! grep -q "botdata" /etc/fstab; then
    echo "LABEL=botdata /opt/botdata ext4 defaults,nofail 0 2" >> /etc/fstab
  fi
  mount -a
  chown -R botuser:botuser /opt/botdata
  info "Data volume mounted at /opt/botdata"
else
  warn "No separate data volume found — using local disk at /opt/botdata"
  warn "Data will NOT persist across instance replacements!"
fi

# ── Firewall (UFW) ────────────────────────────────────────────────────────────
info "Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw --force enable
ufw status

# ── Logrotate config ──────────────────────────────────────────────────────────
info "Configuring log rotation..."
cat > /etc/logrotate.d/discord-bot <<'EOF'
/var/log/discord-bot/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
    dateext
}
EOF

# ── systemd service ───────────────────────────────────────────────────────────
info "Installing systemd service..."
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
if [[ -f "$SCRIPT_DIR/discord-bot.service" ]]; then
  cp "$SCRIPT_DIR/discord-bot.service" /etc/systemd/system/discord-bot.service
  systemctl daemon-reload
  systemctl enable discord-bot.service
  info "Service installed and enabled (will start after deploy.sh)"
else
  warn "discord-bot.service not found at $SCRIPT_DIR — install it manually"
fi

info ""
info "=== Setup complete! ==="
info "Next step: Run deploy.sh to install the application"
info "  sudo -u botuser /opt/discord-bot/scripts/deploy.sh"
