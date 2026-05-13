import sqlite3
from datetime import datetime, timedelta
from mcops.config import STATS_DB_FILE

# ─────────────────────────────────────────────
# DB INIT
# ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(STATS_DB_FILE)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS player_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name  VARCHAR(16) NOT NULL,
            event_type   VARCHAR(10) NOT NULL,
            target_server VARCHAR(64),
            timestamp    DATETIME NOT NULL
        );
        CREATE TABLE IF NOT EXISTS player_peaks (
            recorded_at      DATETIME PRIMARY KEY,
            concurrent_players INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_player_sessions_ts
            ON player_sessions(timestamp);
    ''')
    conn.commit()
    conn.close()

init_db()


def get_connection():
    return sqlite3.connect(STATS_DB_FILE, check_same_thread=False)


# ─────────────────────────────────────────────
# EVENT RECORDING  (called by Plugin API)
# ─────────────────────────────────────────────

def record_event(player_name: str, event_type: str, target_server: str,
                 timestamp: datetime = None) -> None:
    if timestamp is None:
        timestamp = datetime.now()
    conn = get_connection()
    conn.execute(
        "INSERT INTO player_sessions (player_name, event_type, target_server, timestamp) "
        "VALUES (?, ?, ?, ?)",
        (player_name, event_type, target_server, timestamp.isoformat())
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# CURRENT PLAYER COUNT
# ─────────────────────────────────────────────

def get_current_player_count() -> int:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    rows = conn.execute(
        "SELECT player_name, event_type FROM player_sessions "
        "WHERE timestamp > ? ORDER BY timestamp ASC",
        (cutoff,)
    ).fetchall()
    conn.close()

    status: dict[str, str] = {}
    for player, event in rows:
        status[player] = event
    return sum(1 for e in status.values() if e == "join")


def get_online_players() -> list[str]:
    """Returns list of player names currently online."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    rows = conn.execute(
        "SELECT player_name, event_type FROM player_sessions "
        "WHERE timestamp > ? ORDER BY timestamp ASC",
        (cutoff,)
    ).fetchall()
    conn.close()

    status: dict[str, str] = {}
    for player, event in rows:
        status[player] = event
    return [p for p, e in status.items() if e == "join"]


def get_players_per_server() -> dict[str, int]:
    """Returns {server_name: player_count} for currently online players."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    rows = conn.execute(
        "SELECT player_name, event_type, target_server FROM player_sessions "
        "WHERE timestamp > ? ORDER BY timestamp ASC",
        (cutoff,)
    ).fetchall()
    conn.close()

    last_server: dict[str, str] = {}
    status: dict[str, str] = {}
    for player, event, server in rows:
        status[player] = event
        if server:
            last_server[player] = server

    counts: dict[str, int] = {}
    for player, event in status.items():
        if event == "join":
            srv = last_server.get(player, "unknown")
            counts[srv] = counts.get(srv, 0) + 1
    return counts


# ─────────────────────────────────────────────
# PEAK TRACKING
# ─────────────────────────────────────────────

def get_peak_today() -> dict:
    conn = get_connection()
    today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
    row = conn.execute(
        "SELECT recorded_at, concurrent_players FROM player_peaks "
        "WHERE recorded_at >= ? ORDER BY concurrent_players DESC LIMIT 1",
        (today_start,)
    ).fetchone()
    conn.close()
    if row:
        return {"time": row[0], "peak": row[1]}
    return {"time": None, "peak": 0}


def get_timeseries(hours: int = 24) -> list[dict]:
    conn = get_connection()
    start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT recorded_at, concurrent_players FROM player_peaks "
        "WHERE recorded_at >= ? ORDER BY recorded_at ASC",
        (start_time,)
    ).fetchall()
    conn.close()
    return [{"time": r[0], "players": r[1]} for r in rows]


def get_recent_events(limit: int = 50) -> list[dict]:
    """Recent join/quit events for live feed."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT player_name, event_type, target_server, timestamp "
        "FROM player_sessions ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [
        {"player": r[0], "event": r[1], "server": r[2], "timestamp": r[3]}
        for r in rows
    ]


# ─────────────────────────────────────────────
# BACKGROUND AGGREGATION (called every 60s)
# ─────────────────────────────────────────────

async def aggregate_player_stats():
    count = get_current_player_count()
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO player_peaks (recorded_at, concurrent_players) VALUES (?, ?)",
        (now, count)
    )
    conn.commit()
    conn.close()
