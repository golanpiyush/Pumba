"""
memory/db_episodic.py

Episodic memory store — specific dated incidents ("2026-08-14: bird
screeched right after the vacuum started"), as opposed to semantic.py's
generalized beliefs ("the bird dislikes loud noises"). Backed by SQLite for
simplicity and zero external dependencies on-device.

Notable events (scored above config: memory.episodic.notability_score_min
by brain/inspector/relevance_scorer.py) get long retention (retention_days_
notable); everything else ages out after retention_days_default. This is
what lets the companion "remember the funny/important stuff" without its
database growing forever from routine sensor chatter.

Inputs: episode dicts {timestamp, topic, payload, notability_score, tags}.
Outputs: query methods used by memory_manager.py and prompt_builder.py's
         memory_context.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class EpisodicDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["episodic"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                topic TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                notability_score REAL NOT NULL,
                tags TEXT
            )
        """)
        self._conn.commit()

    def insert_episode(self, topic: str, payload: Dict[str, Any], notability_score: float,
                        tags: Optional[List[str]] = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO episodes (timestamp, topic, payload_json, notability_score, tags) VALUES (?, ?, ?, ?, ?)",
            (time.time(), topic, json.dumps(payload), notability_score, ",".join(tags or [])),
        )
        self._conn.commit()
        return cur.lastrowid

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, timestamp, topic, payload_json, notability_score, tags "
            "FROM episodes ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search_by_tag(self, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, timestamp, topic, payload_json, notability_score, tags "
            "FROM episodes WHERE tags LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{tag}%", limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def purge_expired(self) -> int:
        now = time.time()
        default_cutoff = now - self.cfg["retention_days_default"] * 86400
        notable_cutoff = now - self.cfg["retention_days_notable"] * 86400
        notability_min = self.cfg["notability_score_min"]
        cur = self._conn.execute(
            "DELETE FROM episodes WHERE "
            "(notability_score < ? AND timestamp < ?) OR "
            "(notability_score >= ? AND timestamp < ?)",
            (notability_min, default_cutoff, notability_min, notable_cutoff),
        )
        self._conn.commit()
        return cur.rowcount

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0], "timestamp": row[1], "topic": row[2],
            "payload": json.loads(row[3]), "notability_score": row[4],
            "tags": row[5].split(",") if row[5] else [],
        }