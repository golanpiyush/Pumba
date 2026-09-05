"""
memory/db_commitments.py

Tracks verbal commitments the person made — promises Pebble should hold
them to, the way a real pet notices "you said we'd go outside" and gets
pointedly restless when it doesn't happen. This is distinct from episodic
memory (which just records what DID happen) and semantic memory (which
records general opinions) — a commitment is a specific, time-bound "you
said you would X by/around Y."

A commitment is created when voice/stt_whisper.py + brain/llm_router.py
detect a promise-shaped utterance ("I'll put you with the bird in a bit",
"give me 20 minutes and I'll take you out"). It's resolved either by:
  - the matching real-world event actually happening (e.g. environment
    context confirms placement in the cage), which marks it fulfilled, or
  - enough time passing unfulfilled that it becomes "overdue," at which
    point brain/personality.py's nag reflex can reference it.

Inputs: commitment dicts {text, made_at, expected_by, kind, subject,
        status}.
Outputs: query methods for overdue/pending commitments, used by a new
         commitment_watchdog running loop.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class CommitmentsDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["commitments"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS commitments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                kind TEXT NOT NULL,            -- e.g. "cage_placement", "walk", "feeding"
                subject TEXT,                   -- e.g. "bird", "dog" — what/who it's about
                made_at REAL NOT NULL,
                expected_by REAL,                -- epoch seconds; NULL if vague ("in a bit")
                grace_period_s REAL NOT NULL,   -- how long to wait past expected_by before nagging
                status TEXT NOT NULL DEFAULT 'pending',  -- pending | fulfilled | broken | forgiven
                resolved_at REAL,
                last_nagged_at REAL
            )
        """)
        self._conn.commit()

    def create_commitment(self, raw_text: str, kind: str, subject: Optional[str],
                           expected_by: Optional[float], grace_period_s: float) -> int:
        cur = self._conn.execute(
            "INSERT INTO commitments (raw_text, kind, subject, made_at, expected_by, "
            "grace_period_s, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (raw_text, kind, subject, time.time(), expected_by, grace_period_s),
        )
        self._conn.commit()
        return cur.lastrowid

    def mark_fulfilled(self, commitment_id: int) -> None:
        self._conn.execute(
            "UPDATE commitments SET status='fulfilled', resolved_at=? WHERE id=?",
            (time.time(), commitment_id),
        )
        self._conn.commit()

    def mark_nagged(self, commitment_id: int) -> None:
        self._conn.execute(
            "UPDATE commitments SET last_nagged_at=? WHERE id=?", (time.time(), commitment_id)
        )
        self._conn.commit()

    def pending_commitments(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, raw_text, kind, subject, made_at, expected_by, grace_period_s, "
            "status, resolved_at, last_nagged_at FROM commitments WHERE status='pending'"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0], "raw_text": row[1], "kind": row[2], "subject": row[3],
            "made_at": row[4], "expected_by": row[5], "grace_period_s": row[6],
            "status": row[7], "resolved_at": row[8], "last_nagged_at": row[9],
        }