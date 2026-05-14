# MCOps Panel

**Minecraft server management panel – no Docker, no overhead.**

---

## ⚡ Installation (1 Command)

```bash
git clone https://github.com/Buddy611/MCops /tmp/mcops && cd /tmp/mcops && sudo bash install.sh
```

Or, if you already have the files:

```bash
sudo bash install.sh

```
Uninstallation:

```bash
sudo bash uninstall.sh
```

The script automatically performs the following:

* ✅ Installs system packages (Python 3, tmux, Java 21, MariaDB, Gradle)
* ✅ Configures **MariaDB database** and local user
* ✅ Creates the system user `mcops`
* ✅ Sets up the directory structure under `/opt/mcops`
* ✅ Configures the Python Virtual Environment + all dependencies
* ✅ Registers & starts the Systemd service
* ✅ Generates a random API key

The panel will be accessible at `http://SERVER-IP:8000` after approximately 1–2 minutes.

---

## 🖥 Features

| Feature | Description |
| --- | --- |
| **Dashboard** | All servers at a glance with status badges and **live player counts** |
| **Create Server** | Automatic JAR download, EULA acceptance, and server.properties setup |
| **Settings Editor** | Configure RAM, ports, MOTD, and game rules directly from the UI |
| **Live Console** | WebSocket terminal directly in your browser with command history |
| **File Manager** | Browse, edit, upload, and delete files via web interface |
| **Plugin Pool** | Global plugins – upload once, assign to multiple servers |
| **Database Manager** | Central MariaDB/MySQL config with **Jinja2 auto-injection** |
| **Velocity Sync** | New servers are automatically added to `velocity.toml` |
| **Analytics API** | Open API for player event tracking (joins/quits) and time-series data |
| **Backup** | One-click ZIP backups for entire server instances |
| **Start/Stop/Restart/Kill** | Full power control via UI, REST API, or Terminal |

---

## 📁 Directory Structure

```
/opt/mcops/
├── instances/          # Running MC servers
│   ├── survival/
│   │   ├── server.jar
│   │   ├── server.properties
│   │   └── ...
│   └── velocity-proxy/
│       └── velocity.toml  ← automatically populated
├── plugin-pool/        # Global plugin JARs (.jar)
├── backups/            # Automatic ZIP backups
├── global/
│   ├── server_registry.json
│   ├── db_config.env      # Global DB credentials
│   ├── injection_rules.json
│   ├── plugin-templates/  # Jinja2 templates for plugin configs
│   └── stats.db           # SQLite analytics database
├── panel/              # Panel code (mcops package)
├── venv/               # Python Virtual Environment
└── logs/
    └── mcops.log

```

---

## 🔧 Supported Server Software

| Software | Download Source | Usage |
| --- | --- | --- |
| **Paper** | PaperMC API | High performance, Spigot plugins |
| **Velocity** | PaperMC API | Proxy (BungeeCord replacement) |
| **Fabric** | FabricMC Meta | Mods & lightweight performance (1.21.x) |

---

---

MCOps features a centralized database management system. Configure your MariaDB/MySQL credentials once in the **Database** tab:

* **Central Config:** All servers can share the same database host.
* **Auto-Injection:** When a server is created (or settings are saved), credentials are automatically injected.
* **Jinja2 Templates:** Injection uses powerful Jinja2 templates located in `global/plugin-templates/`.
* **Custom Rules:** Map any file path (e.g., `plugins/LuckPerms/config.yml`) to a template in `injection_rules.json`.

---

## ⚙️ Server Settings Editor

No more manual editing of `server.properties`. The integrated editor allows you to:
* Change **RAM allocation** (GB)
* Update **Server Port**
* Toggle **Online-Mode**, **PVP**, and **Difficulty**
* Edit **MOTD** and **Max Players**
* Changes are applied after a server restart.

---

## 📦 Global Plugin Pool

Manage your plugins centrally:
* **Upload:** Drag & drop `.jar` files into the Plugin Pool.
* **Deploy:** Select plugins during server creation to have them automatically installed.
* **Persistence:** Deleting a server does not delete the global plugin from the pool.

---

## 🔗 Velocity Auto-Sync

If a Velocity proxy server is present in `instances/` (identified by `velocity.toml`), every newly created server is **automatically** added to the `velocity.toml` and a `velocity reload` command is triggered.

No more manual editing of `velocity.toml` required.

---

## 🛠 Management

```bash
# Check status
systemctl status mcops

# Restart (after code changes)
systemctl restart mcops

# View live logs
journalctl -u mcops -f

# Change panel port
systemctl edit mcops   # Environment=MCOPS_PORT=9000
systemctl restart mcops
```

---

## 🔑 API

### Create Server

```bash
curl -X POST http://localhost:8000/api/server/create \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "server_name": "Your_Server_Name",
    "software": "Your_Server_Software",
    "version": "Your_Server_Version",
    "ram_gb": 4,
    "plugins": ["Your_Plugin_Name"],
    "start_after_creation": true
  }'
```

### Server Action (Start/Stop/Restart/Kill)

```bash
curl -X POST http://localhost:8000/api/server/action \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "server_name": "Your_Server_Name",
    "action": "start | stop | restart | kill"
  }'
```

### Global Statistics

```bash
curl -X GET "http://localhost:8000/api/stats?api_key=YOUR_API_KEY"
```

**Response Example:**
```json
{
  "current_players": 5,
  "online_players": ["Player1", "Player2"],
  "per_server": {"Server 1": 3, "Server 2": 2},
  "server_info": {
    "Server 1": {
      "status": "online",
      "software": "Your_Software",
      "version": "Your_Version",
      "port": 25565,
      "ram_gb": 4,
      "plugins": ["Your_Plugin"],
      "players": 3
    },
    "Server 2": {
      "status": "offline",
      "software": "Your_Software",
      "version": "Your_Version",
      "port": 25577,
      "ram_gb": 2,
      "plugins": [],
      "players": 2
    }
  },
  "peak_today": {"time": "2024-05-14T10:00:00", "peak": 12},
  "timeseries": [{"time": "...", "players": 5}, ...],
  "recent_events": [{"player": "Player1", "event": "join", "server": "Server 1", "timestamp": "..."}]
}
```

### Push Player Event

```bash
curl -X POST http://localhost:8000/api/stats/event \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "player": "PlayerName",
    "event": "join",
    "server": "Your_Server_Name"
  }'
```