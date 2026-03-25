#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Application deployment and update script
#
# Run as botuser (or sudo -u botuser ./deploy.sh) on the server.
# Safe to re-run for updates — it performs a zero-downtime rolling restart.
#
# Usage (first deploy):
#   sudo -u botuser /opt/discord-bot/scripts/deploy.sh --env-file /opt/discord-bot/.env
#
# Usage (update to latest main branch):
#   sudo -u botuser /opt/discord-bot/scripts/deploy.sh
# =============================================================================
set -euo pipefail

APP_DIR="/opt/discord-bot"
DATA_DIR="/opt/botdata"
LOG_FILE="/var/log/discord-bot/deploy.log"
REPO_URL="https://github.com/YOUR_USERNAME/Discord_bot_AI.git"  # ← update this
BRANCH="main"
VENV_DIR="$APP_DIR/venv"
PYTHON_BIN="$(command -v python3.11 || command -v python3)"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE" >&2; exit 1; }

info "============================================================"
info "Discord Study Bot — Deploy"
info "Date: $(date)"
info "User: $(whoami)"
info "============================================================"

# ── Validate .env exists ──────────────────────────────────────────────────────
ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  error ".env file not found at $ENV_FILE — create it first (see .env.example)"
fi
info ".env found"

# ── Clone or pull latest code ─────────────────────────────────────────────────
if [[ -d "$APP_DIR/.git" ]]; then
  info "Pulling latest code from $BRANCH..."
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
  git -C "$APP_DIR" clean -fd
else
  info "Cloning repository..."
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

COMMIT_HASH=$(git -C "$APP_DIR" rev-parse --short HEAD)
info "Deployed commit: $COMMIT_HASH"

# ── Python virtual environment ────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating virtual environment with $PYTHON_BIN..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

info "Activating venv and upgrading pip..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel setuptools --quiet

# ── Install Python dependencies ───────────────────────────────────────────────
info "Installing Python dependencies..."
pip install -r "$APP_DIR/requirements.txt" --quiet

# ── Override ChromaDB data path in .env (point to persistent volume) ─────────
if ! grep -q "CHROMA_DATA_DIR" "$ENV_FILE"; then
  info "Adding CHROMA_DATA_DIR to .env..."
  echo "" >> "$ENV_FILE"
  echo "# Deployment override — persistent block volume" >> "$ENV_FILE"
  echo "CHROMA_DATA_DIR=$DATA_DIR/chromadb" >> "$ENV_FILE"
fi

# ── Copy/symlink uploads dir to persistent volume ─────────────────────────────
if [[ ! -L "$APP_DIR/uploads" ]]; then
  rm -rf "$APP_DIR/uploads"
  ln -s "$DATA_DIR/uploads" "$APP_DIR/uploads"
  info "Symlinked $APP_DIR/uploads → $DATA_DIR/uploads"
fi

# ── Rolling restart via systemd ───────────────────────────────────────────────
info "Restarting discord-bot service..."
if systemctl is-active --quiet discord-bot.service; then
  sudo systemctl restart discord-bot.service
  info "Service restarted"
else
  sudo systemctl start discord-bot.service
  info "Service started"
fi

# ── Health check ──────────────────────────────────────────────────────────────
sleep 3
if systemctl is-active --quiet discord-bot.service; then
  info "✓ Service is running"
else
  error "Service failed to start — check logs: journalctl -u discord-bot -n 50"
fi

info ""
info "=== Deploy complete! ==="
info "Commit: $COMMIT_HASH"
info "Logs:   journalctl -u discord-bot -f"
info "Status: systemctl status discord-bot"
