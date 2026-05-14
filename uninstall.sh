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
step "1/7 – Stopping MCOps Service"
systemctl stop mcops 2>/dev/null || true
systemctl disable mcops 2>/dev/null || true
rm -f /etc/systemd/system/mcops.service
systemctl daemon-reload
ok "Service stopped and removed"

# 2. Kill all processes of the mcops user
step "2/7 – Terminating all MCOps processes"
if id "$MCOPS_USER" &>/dev/null; then
    pkill -u "$MCOPS_USER" || true
    sleep 2
    pkill -9 -u "$MCOPS_USER" || true
    ok "All processes for user $MCOPS_USER terminated"
fi

# 3. Stop Minecraft servers (tmux)
step "3/7 – Stopping all Minecraft servers"
if command -v tmux &>/dev/null; then
    sessions=$(tmux ls -F '#S' 2>/dev/null | grep '^mc_' || true)
    for s in $sessions; do
        tmux kill-session -t "$s" 2>/dev/null || true
        ok "Killed session $s"
    done
fi
ok "All tmux sessions handled"

# 4. Database
step "4/7 – Removing MariaDB Database & User"
mysql -u root <<SQLEOF || warn "Could not remove database. Maybe MariaDB is not running?"
DROP DATABASE IF EXISTS \`${DB_NAME}\`;
DROP USER IF EXISTS '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQLEOF
ok "Database and user removed"

# 5. User
step "5/7 – Removing System User"
if id "$MCOPS_USER" &>/dev/null; then
    userdel -r -f "$MCOPS_USER" 2>/dev/null || true
    ok "User '$MCOPS_USER' removed"
else
    ok "User '$MCOPS_USER' does not exist"
fi

# 6. Directories
step "6/7 – Deleting Files"
[[ -d "$BASE_DIR" ]] && rm -rf "$BASE_DIR" && ok "Directory $BASE_DIR deleted"
[[ -d "/tmp/mcops" ]] && rm -rf "/tmp/mcops" && ok "Temporary install directory /tmp/mcops deleted"

# 7. Final cleanup
step "7/7 – Finalizing"
ok "MCOps has been completely removed from your system."
echo -e "  You can now reinstall using the 1-command installer."
echo ""
