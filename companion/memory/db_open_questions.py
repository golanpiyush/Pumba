"""
memory/db_open_questions.py

Holds unresolved ambiguity — the "wait, what/who is that?" state. When
something is said that doesn't cleanly match anything known (an unfamiliar
name with no clear referent), instead of guessing or ignoring it, Pebble
files an open question and asks about it at the next natural moment. This
is short-lived working memory, not permanent storage — most open questions
resolve within the same conversation or shortly after.

This is what makes "smart enough to ask" structurally real rather than
just an LLM improvising a question once: the question object persists
across turns, so if you don't answer immediately, Pebble can circle back
("wait, you never told me who Ken is") rather than the ambiguity silently
evaporating.

Inputs: candidate_referent (the confusing word/phrase), context describing
        why it was flagged.
Outputs: query methods for brain/entity_resolver.py and personality.py's
         curiosity reflex.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class OpenQuestionsDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["open_questions"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS open_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_referent TEXT NOT NULL,     -- e.g. "Ken"
                source_utterance TEXT NOT NULL,
                raised_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',   -- open | resolved | abandoned
                resolved_as TEXT,                        -- e.g. "bird_name:entity_id=4"
                resolved_at REAL
            )
        """)
        self._conn.commit()

    def raise_question(self, candidate_referent: str, source_utterance: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO open_questions (candidate_referent, source_utterance, raised_at, status) "
            "VALUES (?, ?, ?, 'open')",
            (candidate_referent, source_utterance, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid

    def resolve(self, question_id: int, resolved_as: str) -> None:
        self._conn.execute(
            "UPDATE open_questions SET status='resolved', resolved_as=?, resolved_at=? WHERE id=?",
            (resolved_as, time.time(), question_id),
        )
        self._conn.commit()

    def abandon_stale(self, max_age_s: float) -> int:
        cutoff = time.time() - max_age_s
        cur = self._conn.execute(
            "UPDATE open_questions SET status='abandoned' WHERE status='open' AND raised_at < ?",
            (cutoff,),
        )
        self._conn.commit()
        return cur.rowcount

    def open_questions(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, candidate_referent, source_utterance, raised_at, status, resolved_as, resolved_at "
            "FROM open_questions WHERE status='open' ORDER BY raised_at DESC"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def most_recent_open(self) -> Optional[Dict[str, Any]]:
        rows = self.open_questions()
        return rows[0] if rows else None

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0], "candidate_referent": row[1], "source_utterance": row[2],
            "raised_at": row[3], "status": row[4], "resolved_as": row[5], "resolved_at": row[6],
        }