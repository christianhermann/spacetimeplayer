#!/usr/bin/env python3
"""PBS Space Time Companion — stdlib HTTP + SQLite server."""
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import closing, contextmanager
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "spacetime.db"
STATIC_DIR = BASE_DIR / "static"

SYNC_STATE = {"running": False, "last_run": None, "message": "Idle", "error": None}


@contextmanager
def get_db(db_path: Path = DB_PATH):
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            yield conn


def init_db(db_path: Path = DB_PATH) -> None:
    with get_db(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                published_at TEXT DEFAULT '',
                upload_index INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                thumbnail TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                auto_topics TEXT DEFAULT '[]',
                related_ids TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                video_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS playlist_videos (
                playlist_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (playlist_id, video_id)
            );

            CREATE TABLE IF NOT EXISTS user_state (
                video_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'unwatched',
                progress_seconds REAL DEFAULT 0,
                is_chosen INTEGER DEFAULT 0,
                queue_order INTEGER DEFAULT 0,
                custom_tags TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def fetch_all_data(db_path: Path = DB_PATH) -> dict:
    # ponytail: single payload (<500KB for ~650 videos) makes client-side filtering instant; paginate only if >5k videos
    with get_db(db_path) as conn:
        videos = []
        for row in conn.execute("SELECT * FROM videos ORDER BY upload_index ASC, published_at DESC"):
            d = dict(row)
            d["auto_topics"] = json.loads(d["auto_topics"] or "[]")
            d["related_ids"] = json.loads(d["related_ids"] or "[]")
            videos.append(d)

        playlists = [dict(r) for r in conn.execute("SELECT * FROM playlists ORDER BY title ASC")]
        playlist_videos = [
            dict(r)
            for r in conn.execute(
                "SELECT playlist_id, video_id, position FROM playlist_videos ORDER BY playlist_id, position ASC"
            )
        ]

        user_state = {}
        for row in conn.execute("SELECT * FROM user_state"):
            d = dict(row)
            d["is_chosen"] = bool(d["is_chosen"])
            d["custom_tags"] = json.loads(d["custom_tags"] or "[]")
            user_state[d["video_id"]] = d

    return {
        "videos": videos,
        "playlists": playlists,
        "playlist_videos": playlist_videos,
        "user_state": user_state,
        "sync": SYNC_STATE,
    }


def upsert_user_state(video_id: str, payload: dict, db_path: Path = DB_PATH) -> dict:
    with get_db(db_path) as conn:
        cur = conn.execute("SELECT * FROM user_state WHERE video_id = ?", (video_id,)).fetchone()
        state = (
            dict(cur)
            if cur
            else {
                "video_id": video_id,
                "status": "unwatched",
                "progress_seconds": 0.0,
                "is_chosen": 0,
                "queue_order": 0,
                "custom_tags": "[]",
                "notes": "",
            }
        )

        if "status" in payload and payload["status"] in ("unwatched", "in_progress", "watched"):
            state["status"] = payload["status"]
        if "progress_seconds" in payload:
            state["progress_seconds"] = max(0.0, float(payload["progress_seconds"]))
        if "is_chosen" in payload:
            state["is_chosen"] = 1 if payload["is_chosen"] else 0
            if state["is_chosen"] and not state.get("queue_order"):
                max_q = conn.execute("SELECT COALESCE(MAX(queue_order), 0) FROM user_state").fetchone()[0]
                state["queue_order"] = max_q + 1
        if "queue_order" in payload:
            state["queue_order"] = int(payload["queue_order"])
        if "custom_tags" in payload:
            tags = payload["custom_tags"]
            state["custom_tags"] = json.dumps(tags if isinstance(tags, list) else [])
        if "notes" in payload:
            state["notes"] = str(payload["notes"])

        conn.execute(
            """
            INSERT INTO user_state (video_id, status, progress_seconds, is_chosen, queue_order, custom_tags, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(video_id) DO UPDATE SET
                status = excluded.status,
                progress_seconds = excluded.progress_seconds,
                is_chosen = excluded.is_chosen,
                queue_order = excluded.queue_order,
                custom_tags = excluded.custom_tags,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                video_id,
                state["status"],
                state["progress_seconds"],
                state["is_chosen"],
                state["queue_order"],
                state["custom_tags"],
                state["notes"],
            ),
        )
        row = dict(conn.execute("SELECT * FROM user_state WHERE video_id = ?", (video_id,)).fetchone())
        row["is_chosen"] = bool(row["is_chosen"])
        row["custom_tags"] = json.loads(row["custom_tags"] or "[]")
        return row


def trigger_sync(full: bool = False, summarize: bool = False) -> bool:
    if SYNC_STATE["running"]:
        return False

    def _run():
        SYNC_STATE["running"] = True
        SYNC_STATE["error"] = None
        SYNC_STATE["message"] = "Syncing PBS Space Time catalog via yt-dlp..."
        try:
            cmd = [sys.executable, str(BASE_DIR / "sync.py")]
            if full:
                cmd.append("--full")
            if summarize:
                cmd.append("--summarize")
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                SYNC_STATE["error"] = (proc.stderr or proc.stdout or "Sync failed").strip()[-500:]
                SYNC_STATE["message"] = "Sync failed"
            else:
                lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
                SYNC_STATE["message"] = lines[-1] if lines else "Sync complete"
                SYNC_STATE["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as exc:
            SYNC_STATE["error"] = str(exc)
            SYNC_STATE["message"] = "Sync error"
        finally:
            SYNC_STATE["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass  # Keep console clean

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/data":
            self._send_json(fetch_all_data())
        elif parsed.path == "/api/sync":
            self._send_json(SYNC_STATE)
        else:
            if parsed.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if parsed.path.startswith("/api/state/"):
            video_id = parsed.path.split("/api/state/", 1)[1].strip("/")
            if not video_id:
                self._send_json({"error": "Missing video_id"}, 400)
                return
            updated = upsert_user_state(video_id, payload)
            self._send_json({"ok": True, "state": updated})
        elif parsed.path == "/api/sync":
            started = trigger_sync(
                full=bool(payload.get("full")),
                summarize=bool(payload.get("summarize")),
            )
            self._send_json({"started": started, "sync": SYNC_STATE})
        else:
            self._send_json({"error": "Not found"}, 404)


def run_self_test():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_db = Path(tmp) / "test.db"
        init_db(test_db)
        with get_db(test_db) as conn:
            conn.execute(
                "INSERT INTO videos (id, title, duration, auto_topics) VALUES (?, ?, ?, ?)",
                ("v1", "The Edge of Space Time", 900, json.dumps(["Cosmology", "Black Holes"])),
            )
        st = upsert_user_state(
            "v1",
            {"status": "in_progress", "progress_seconds": 125.5, "is_chosen": True, "custom_tags": ["fav"], "notes": "Great intro"},
            db_path=test_db,
        )
        assert st["status"] == "in_progress"
        assert st["progress_seconds"] == 125.5
        assert st["is_chosen"] is True
        assert st["custom_tags"] == ["fav"]
        data = fetch_all_data(test_db)
        assert len(data["videos"]) == 1
        assert data["videos"][0]["auto_topics"] == ["Cosmology", "Black Holes"]
        assert data["user_state"]["v1"]["notes"] == "Great intro"
    print("Self-test passed!")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_self_test()
        sys.exit(0)

    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"PBS Space Time Companion running at {url}")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
