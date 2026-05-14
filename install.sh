#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║          MCOps Panel – One-Command Installer                         ║
# ║          Usage: sudo bash install.sh                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "\n${BOLD}${BLUE}[$(date +%H:%M:%S)] $1${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; exit 1; }
info()  { echo -e "  ${CYAN}→${NC} $1"; }

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
  __  __  ____   ___               ____                  _
 |  \/  |/ ___| / _ \ _ __  ___  |  _ \ __ _ _ __   ___| |
 | |\/| | |    | | | | '_ \/ __| | |_) / _` | '_ \ / _ \ |
 | |  | | |___ | |_| | |_) \__ \ |  __/ (_| | | | |  __/ |
 |_|  |_|\____| \___/| .__/|___/ |_|   \__,_|_| |_|\___|_|
                      |_|
EOF
echo -e "${NC}${BOLD}  Minecraft Server Management Panel – Auto-Installer v2.0${NC}\n"

# ── Root check ──────────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && err "Bitte als root ausführen: sudo bash install.sh"

# ── Config ──────────────────────────────────────────────────────────────
MCOPS_USER="${MCOPS_USER:-mcops}"
BASE_DIR="${BASE_DIR:-/opt/mcops}"
PORT="${MCOPS_PORT:-8000}"
API_KEY="$(openssl rand -hex 16 2>/dev/null || cat /dev/urandom | tr -dc 'a-f0-9' | head -c 32)"
DB_NAME="mcops"
DB_USER="mcops"
DB_PASS="$(openssl rand -base64 18 | tr -d '+/=')"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PANEL_DIR="$BASE_DIR/panel"
VENV_DIR="$BASE_DIR/venv"

echo -e "  ${CYAN}Verzeichnis:${NC}  $BASE_DIR"
echo -e "  ${CYAN}Port:${NC}         $PORT"
echo -e "  ${CYAN}System-User:${NC}  $MCOPS_USER"

# ════════════════════════════════════════════════════════════════════════
step "1/7 – System-Pakete installieren"
# ════════════════════════════════════════════════════════════════════════
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>/dev/null
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    tmux \
    openjdk-21-jdk \
    curl wget unzip zip \
    sqlite3 \
    mariadb-server \
    gradle \
    2>/dev/null || true

# Fallback: try openjdk-17 if 21 not available
java -version &>/dev/null || apt-get install -y -qq openjdk-17-jdk 2>/dev/null || true
java -version &>/dev/null || err "Java konnte nicht installiert werden"
ok "System-Pakete installiert (Java, tmux, MariaDB, Gradle)"

# ════════════════════════════════════════════════════════════════════════
step "2/7 – MariaDB einrichten"
# ════════════════════════════════════════════════════════════════════════
systemctl start mariadb
systemctl enable mariadb

# Create DB + user
mysql -u root <<SQLEOF
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQLEOF

ok "MariaDB Datenbank '${DB_NAME}' und Benutzer '${DB_USER}' erstellt"

# ════════════════════════════════════════════════════════════════════════
step "3/7 – Benutzer & Verzeichnisse"
# ════════════════════════════════════════════════════════════════════════
if ! id "$MCOPS_USER" &>/dev/null; then
    useradd -r -s /bin/bash -m -d "$BASE_DIR" "$MCOPS_USER"
    ok "System-User '$MCOPS_USER' erstellt"
else
    ok "User '$MCOPS_USER' existiert bereits"
fi

mkdir -p \
    "$PANEL_DIR" \
    "$BASE_DIR/instances" \
    "$BASE_DIR/plugin-pool" \
    "$BASE_DIR/templates" \
    "$BASE_DIR/backups" \
    "$BASE_DIR/global/plugin-templates" \
    "$BASE_DIR/logs"

ok "Verzeichnisstruktur angelegt unter $BASE_DIR"

# ════════════════════════════════════════════════════════════════════════
step "4/7 – Panel-Code installieren"
# ════════════════════════════════════════════════════════════════════════
cp -r "$SOURCE_DIR/mcops" "$PANEL_DIR/"
ok "mcops Paket kopiert"

# Touch __init__ files
touch "$PANEL_DIR/mcops/__init__.py"
touch "$PANEL_DIR/mcops/modules/__init__.py"
touch "$PANEL_DIR/mcops/api/__init__.py"

# Generate production config.py
cat > "$PANEL_DIR/mcops/config.py" << PYEOF
import sys
from pathlib import Path

BASE_DIR          = Path("$BASE_DIR")
INSTANCES_DIR     = BASE_DIR / "instances"
PLUGIN_POOL_DIR   = BASE_DIR / "plugin-pool"
TEMPLATES_DIR     = BASE_DIR / "templates"
BACKUPS_DIR       = BASE_DIR / "backups"
GLOBAL_DIR        = BASE_DIR / "global"
DB_CONFIG_FILE    = GLOBAL_DIR / "db_config.env"
SERVER_REGISTRY_FILE = GLOBAL_DIR / "server_registry.json"
INJECTION_RULES_FILE = GLOBAL_DIR / "injection_rules.json"
PLUGIN_TEMPLATES_DIR = GLOBAL_DIR / "plugin-templates"
STATS_DB_FILE     = GLOBAL_DIR / "stats.db"
MCOPS_DIR         = Path(__file__).parent.resolve()

for _d in [INSTANCES_DIR, PLUGIN_POOL_DIR, TEMPLATES_DIR,
           BACKUPS_DIR, GLOBAL_DIR, PLUGIN_TEMPLATES_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
PYEOF

# Write db_config.env with real credentials
cat > "$BASE_DIR/global/db_config.env" << ENVEOF
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_NAME=${DB_NAME}
ENVEOF

# Default JSON files
# Default JSON files
[[ -f "$BASE_DIR/global/server_registry.json" ]] || echo '{}' > "$BASE_DIR/global/server_registry.json"

cat > "$BASE_DIR/global/injection_rules.json" << 'JSONEOF'
{
  "plugins/LuckPerms/config.yml": "luckperms_config.yml.j2"
}
JSONEOF

# Create LuckPerms template
cat > "$BASE_DIR/global/plugin-templates/luckperms_config.yml.j2" << 'LPEOF'
server-name: "mcops_{{ DB_NAME }}"
storage-method: MariaDB
data:
  address: "{{ DB_HOST }}:{{ DB_PORT }}"
  database: "{{ DB_NAME }}"
  username: "{{ DB_USER }}"
  password: "{{ DB_PASSWORD }}"
  pool-settings:
    maximum-pool-size: 10
    minimum-idle: 10
    maximum-lifetime: 1800000
    connection-timeout: 5000
  table-prefix: "luckperms_"
messaging-service: "sql"
LPEOF


# Entrypoint
cat > "$PANEL_DIR/run.py" << 'PYEOF'
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import uvicorn
from mcops.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("MCOPS_PORT", 8000)),
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=30,
    )
PYEOF

ok "Panel-Code & Konfiguration fertig"

# ════════════════════════════════════════════════════════════════════════
step "5/7 – Python Virtual Environment & Dependencies"
# ════════════════════════════════════════════════════════════════════════
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet \
    fastapi \
    "uvicorn[standard]" \
    libtmux \
    jinja2 \
    cachetools \
    python-multipart \
    websockets \
    aiofiles

ok "Python-Pakete installiert"

# ════════════════════════════════════════════════════════════════════════
step "6/7 – MCOps Plugin kompilieren & in Pool installieren"
# ════════════════════════════════════════════════════════════════════════
PLUGIN_SRC="$SOURCE_DIR/mcops-plugin"
PLUGIN_BUILD_DIR="/tmp/mcops-plugin-build"

if [[ -d "$PLUGIN_SRC" ]]; then
    cp -r "$PLUGIN_SRC" "$PLUGIN_BUILD_DIR"
    cd "$PLUGIN_BUILD_DIR"

    # Use system gradle or download wrapper
    if command -v gradle &>/dev/null; then
        info "Kompiliere Plugins mit System-Gradle..."
        gradle build --no-daemon --quiet 2>/dev/null
    else
        # Fallback: download gradle wrapper
        info "Lade Gradle Wrapper herunter..."
        wget -q "https://services.gradle.org/distributions/gradle-8.5-bin.zip" -O /tmp/gradle.zip
        unzip -q /tmp/gradle.zip -d /tmp/
        GRADLE_BIN=$(ls -d /tmp/gradle-*/bin/gradle | head -1)
        "$GRADLE_BIN" build --no-daemon --quiet 2>/dev/null
    fi

    if [[ -f "mcops-bukkit/build/libs/MCOpsPlugin-Paper.jar" ]]; then
        cp "mcops-bukkit/build/libs/MCOpsPlugin-Paper.jar" "$BASE_DIR/plugin-pool/"
        cp "mcops-velocity/build/libs/MCOpsPlugin-Velocity.jar" "$BASE_DIR/plugin-pool/"
        cp "mcops-fabric/build/libs/MCOpsPlugin-Fabric.jar" "$BASE_DIR/plugin-pool/"
        ok "MCOpsPlugin JARs (Paper, Velocity, Fabric) → $BASE_DIR/plugin-pool/"
    else
        warn "Plugin-Build fehlgeschlagen. Manuell kompilieren: cd $PLUGIN_BUILD_DIR && gradle build"
        # Create a marker so the UI knows
        echo "BUILD_FAILED" > "$BASE_DIR/plugin-pool/.mcops-plugin-build-failed"
    fi

    cd "$SOURCE_DIR"
else
    warn "mcops-plugin Verzeichnis nicht gefunden – Plugin-Build übersprungen."
fi

info "Lade LuckPerms (Open Source Basis für Netzwerksynchronisation) herunter..."
wget -q "https://download.luckperms.net/1575/bukkit/loader/LuckPerms-Bukkit-5.4.150.jar" -O "$BASE_DIR/plugin-pool/LuckPerms-Bukkit.jar" || true
wget -q "https://download.luckperms.net/1575/velocity/LuckPerms-Velocity-5.4.150.jar" -O "$BASE_DIR/plugin-pool/LuckPerms-Velocity.jar" || true
ok "LuckPerms heruntergeladen"

# ════════════════════════════════════════════════════════════════════════
step "7/7 – Systemd Service einrichten & starten"
# ════════════════════════════════════════════════════════════════════════
chown -R "$MCOPS_USER:$MCOPS_USER" "$BASE_DIR"

cat > /etc/systemd/system/mcops.service << SVCEOF
[Unit]
Description=MCOps Minecraft Panel
After=network.target mariadb.service
Wants=mariadb.service

[Service]
Type=simple
User=$MCOPS_USER
WorkingDirectory=$PANEL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="MCOPS_PORT=$PORT"
Environment="MCOPS_API_KEY=$API_KEY"
ExecStart=$VENV_DIR/bin/python run.py
Restart=on-failure
RestartSec=5
StandardOutput=append:$BASE_DIR/logs/mcops.log
StandardError=append:$BASE_DIR/logs/mcops.log

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable mcops
systemctl restart mcops
sleep 3

SERVER_IP=$(hostname -I | awk '{print $1}')

if systemctl is-active --quiet mcops; then
    STATUS="${GREEN}LÄUFT${NC}"
else
    STATUS="${RED}FEHLER${NC} – prüfe: journalctl -u mcops -n 30"
fi

# ════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║       MCOps Panel erfolgreich installiert!               ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Panel:${NC}        ${CYAN}http://${SERVER_IP}:${PORT}${NC}"
echo -e "  ${BOLD}Status:${NC}       $(echo -e $STATUS)"
echo -e "  ${BOLD}API Key:${NC}      ${YELLOW}${API_KEY}${NC}"
echo ""
echo -e "  ${BOLD}Datenbank:${NC}"
echo -e "    Host:     127.0.0.1:3306"
echo -e "    DB:       ${DB_NAME}"
echo -e "    User:     ${DB_USER}"
echo -e "    Passwort: ${YELLOW}${DB_PASS}${NC}"
echo ""
echo -e "  ${BOLD}Plugin Pool:${NC}  $BASE_DIR/plugin-pool/"
echo -e "  ${BOLD}Server-Daten:${NC} $BASE_DIR/instances/"
echo -e "  ${BOLD}Logs:${NC}         journalctl -u mcops -f"
echo ""
echo -e "  ${YELLOW}⚠  Speichere API Key und DB-Passwort sicher!${NC}"
echo ""
