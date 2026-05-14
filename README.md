# 🛡️ MCOps Panel
**Lightweight, robust, and Docker-free Minecraft Server Management.**

MCOps is a modern, high-performance management panel for Minecraft networks. It focuses on speed, simplicity, and deep integration with system tools like `tmux` and `systemd`, eliminating the overhead of containerization.

---

## 🚀 Quick Start

### 📦 Installation
The one-command installer handles everything: dependencies, database setup, and service registration.

```bash
# Clone and install in one go
git clone https://github.com/Buddy611/MCops /tmp/mcops && cd /tmp/mcops && sudo bash install.sh
```

**What the installer does:**
* ✅ **System Core:** Installs Python 3, tmux, Java 21, MariaDB, and Gradle.
* ✅ **Database:** Fully configures a local **MariaDB instance** for your network.
* ✅ **Security:** Creates a dedicated `mcops` system user and generates a unique **128-bit API Key**.
* ✅ **Service:** Registers and starts the `mcops.service` via Systemd.

### 🗑️ Uninstallation
Need a clean slate? The uninstaller removes everything safely.

```bash
# Run the uninstaller from the repo directory
sudo bash uninstall.sh
```
*⚠️ Warning: This will permanently delete all panel data, server instances, and databases.*

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **📊 Dashboard** | Real-time overview of all servers, status badges, and live player counts. |
| **🛠️ Server Creator** | Zero-config server setup. Select software, version, RAM, and plugins. |
| **💻 Web Console** | Full-duplex WebSocket terminal with command history and live output. |
| **📂 File Manager** | Integrated web-based IDE to edit, upload, move, or delete files. |
| **🔌 Plugin Pool** | Upload once, deploy everywhere. Manage plugins centrally for the whole network. |
| **🗄️ DB Injection** | Auto-inject MariaDB/MySQL credentials into plugin configs via Jinja2 templates. |
| **🌐 Velocity Sync** | Automatic proxy synchronization—new servers are added to Velocity instantly. |
| **🛡️ Backup System** | One-click ZIP backups for entire server instances. |
| **🔑 Secure API** | Full REST API for automation, player tracking, and status monitoring. |

---

## 🔒 Security & Privacy
* **Hardened API:** Access is restricted via a mandatory, randomly generated `MCOPS_API_KEY`.
* **Safe Defaults:** No hardcoded passwords or insecure fallbacks.
* **Privacy Focused:** Environment-aware configuration; no personal paths or sensitive data in code.
* **Clean Repo:** Strict `.gitignore` policy to prevent accidental leaks of `.env` or `.db` files.

---

## 📁 Directory Structure
MCOps follows a clean, standardized structure under `/opt/mcops/`:

```text
/opt/mcops/
├── 🏰 instances/        # All running Minecraft servers
├── 📥 plugin-pool/      # Centralized JAR storage
├── 💾 backups/          # Compressed server backups
├── ⚙️ global/           # System-wide configs, DB env, and registry
├── 🖥️ panel/            # Core MCOps Panel application code
├── 🐍 venv/             # Isolated Python environment
└── 📝 logs/             # Centralized panel logs
```

---

## 🔧 Supported Software
| Software | Version Support | Ideal For |
| :--- | :--- | :--- |
| **Paper** | Latest & Legacy | High-performance Spigot/Bukkit plugins (inc. 1.21.2). |
| **Velocity** | Latest | The modern, fast, and secure proxy (inc. 1.21.2). |
| **Fabric** | 1.14+ | Modded servers and performance (inc. 1.21.2). |

---

## 🛠 Management Commands

```bash
# Check if the panel is running
systemctl status mcops

# Restart the panel (e.g., after a git pull)
systemctl restart mcops

# Watch live logs
journalctl -u mcops -f

# Custom Port: Use 'systemctl edit mcops' to set MCOPS_PORT environment.
```

---

## 🔗 Automation API

MCOps provides a powerful JSON API for external automation.

### Create a Server
`POST /api/server/create`
```json
-d '{
  "api_key": "YOUR_KEY",
  "server_name": "Skyblock_01",
  "software": "paper",
  "version": "1.21.2",
  "ram_gb": 4,
  "plugins": ["LuckPerms", "EssentialsX"]
}'

```

### Server Actions
`POST /api/server/action`
```json
{
  "api_key": "YOUR_KEY",
  "server_name": "Skyblock_01",
  "action": "start | stop | restart | kill"
}
```

---

*Built with ❤️ for the Minecraft Community.*
