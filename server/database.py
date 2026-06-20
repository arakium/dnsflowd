import sqlite3
import bridge
from typing import Dict, List, Tuple

DB_FILE = "dns_traffic.db"


def setup_db() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dns_traffic (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                log_type  TEXT,
                src_ip    TEXT,
                dst_ip    TEXT,
                detail    TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_detail_src ON dns_traffic (detail, src_ip)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_blocked_domain ON blocked_domains (domain)")
    print("[Database] Setup complete.")


def insert_data(data: Dict) -> None:
    detail = data.get("domain") if data.get("type") == "QUERY" else data.get("data")

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO dns_traffic (log_type, src_ip, dst_ip, detail)
            VALUES (?, ?, ?, ?)
        """, (data.get("type"), data.get("src"), data.get("dst"), detail))

    if data.get("type") == "QUERY":
        bridge.live_traffic_queue.put({
            "src_ip": data.get("src"),
            "domain": detail,
        })

def get_recent_queries(limit: int = 200) -> List[Dict]:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, log_type, src_ip, detail, dst_ip
            FROM dns_traffic
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return [
            {
                "timestamp": row[0],
                "type":      row[1],
                "src_ip":    row[2],
                "domain":    row[3],
                "dst_ip":    row[4],
            }
            for row in cur.fetchall()
        ]


def get_stats() -> Dict:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dns_traffic")
        total_events = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM dns_traffic
            WHERE log_type = 'QUERY'
            AND timestamp >= datetime('now', '-1 minute')
        """)
        queries_per_min = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT detail) FROM dns_traffic
            WHERE log_type = 'QUERY'
            AND timestamp >= datetime('now', '-1 hour')
        """)
        unique_domains = cur.fetchone()[0]

    return {
        "total_events":    total_events,
        "queries_per_min": queries_per_min,
        "unique_domains":  unique_domains,
    }


def get_top_talkers(limit: int = 10) -> List[Tuple[str, int]]:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT src_ip, COUNT(*) AS request_count
            FROM dns_traffic
            WHERE log_type = 'QUERY'
            GROUP BY src_ip
            ORDER BY request_count DESC
            LIMIT ?
        """, (limit,))
        return cur.fetchall()


def get_all_blocked_domains() -> List[str]:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT domain FROM blocked_domains ORDER BY id DESC")
        return [row[0] for row in cur.fetchall()]


def add_to_blocklist(domain: str) -> bool:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO blocked_domains (domain) VALUES (?)", (domain,)
            )
        return True
    except sqlite3.IntegrityError:
        return False  # already exists


def remove_from_blocklist(domain: str) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute(
            "DELETE FROM blocked_domains WHERE domain = ?", (domain,)
        )
        return cur.rowcount > 0  # False if domain wasn't there

if __name__ == "__main__":
    setup_db()