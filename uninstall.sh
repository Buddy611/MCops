#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║          MCOps Panel – Uninstaller                                   ║
# ║          Usage: sudo bash uninstall.sh                               ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "\n${BOLD}${BLUE}[$(date +%H:%M:%S)] $1${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; exit 1; }

[[ "$EUID" -ne 0 ]] && err "Please run as root: sudo bash uninstall.sh"

MCOPS_USER="mcops"
BASE_DIR="/opt/mcops"
DB_NAME="mcops"
DB_USER="mcops"

echo -e "${RED}${BOLD}"
echo "  WARNING: This will PERMANENTLY remove MCOps and ALL server data!"
echo -e "${NC}"
read -p "  Are you sure you want to continue? (y/N): " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 1

# 1. Stop service
step "1/6 – Stopping MCOps Service"
systemctl stop mcops 2>/dev/null || true
systemctl disable mcops 2>/dev/null || true
rm -f /etc/systemd/system/mcops.service
systemctl daemon-reload
ok "Service stopped and removed"

# 2. Stop Minecraft servers (tmux)
step "2/6 – Stopping all Minecraft servers"
if command -v tmux &>/dev/null; then
    # Kill all sessions starting with mc_
    sessions=$(tmux ls -F '#S' 2>/dev/null | grep '^mc_' || true)
    for s in $sessions; do
        tmux kill-session -t "$s"
        ok "Killed session $s"
    done
fi
ok "All tmux sessions handled"

# 3. Database
step "3/6 – Removing MariaDB Database & User"
mysql -u root <<SQLEOF || warn "Could not remove database. Maybe MariaDB is not running?"
DROP DATABASE IF EXISTS \`${DB_NAME}\`;
DROP USER IF EXISTS '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQLEOF
ok "Database and user removed"

# 4. User
step "4/6 – Removing System User"
if id "$MCOPS_USER" &>/dev/null; then
    userdel -r "$MCOPS_USER" 2>/dev/null || userdel -f "$MCOPS_USER"
    ok "User '$MCOPS_USER' removed"
else
    ok "User '$MCOPS_USER' does not exist"
fi

# 5. Directories
step "5/6 – Deleting Files"
if [[ -d "$BASE_DIR" ]]; then
    rm -rf "$BASE_DIR"
    ok "Directory $BASE_DIR deleted"
fi

# 6. Final cleanup
step "6/6 – Finalizing"
ok "MCOps has been completely removed from your system."
echo ""
