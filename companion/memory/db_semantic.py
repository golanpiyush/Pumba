"""
memory/db_semantic.py

Semantic memory store — generalized beliefs distilled FROM episodic memory
by memory_manager.py's consolidation pass, e.g. {"subject": "bird",
"predicate": "dislikes", "object": "loud noises", "confidence": 0.8}.
This is what lets "opinions about the bird, dog, and me evolve" — a belief
here typically starts as a single episodic note and only gets promoted
after config: memory.consolidation.min_repeats_for_pattern similar episodes.

Inputs: fact dicts (validated upstream by brain/inspector/fact_inspector.py
        and brain/inspector/contradiction_check.py).
Outputs: query methods keyed by subject, used by prompt_builder.py to give
         the LLM "what I already believe about X" context.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class SemanticDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["semantic"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL NOT NULL,
                last_updated REAL NOT NULL,
                support_count INTEGER NOT NULL DEFAULT 1
            )
        """)
        self._conn.commit()

    def upsert_fact(self, subject: str, predicate: str, object_: str, confidence: float) -> None:
        existing = self._conn.execute(
            "SELECT id, support_count FROM facts WHERE subject=? AND predicate=? AND object=?",
            (subject, predicate, object_),
        ).fetchone()
        if existing:
            fact_id, support_count = existing
            self._conn.execute(
                "UPDATE facts SET confidence=?, last_updated=?, support_count=? WHERE id=?",
                (confidence, time.time(), support_count + 1, fact_id),
            )
        else:
            self._enforce_max_facts_per_subject(subject)
            self._conn.execute(
                "INSERT INTO facts (subject, predicate, object, confidence, last_updated, support_count) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (subject, predicate, object_, confidence, time.time()),
            )
        self._conn.commit()

    def _enforce_max_facts_per_subject(self, subject: str) -> None:
        max_facts = self.cfg["max_facts_per_subject"]
        count = self._conn.execute("SELECT COUNT(*) FROM facts WHERE subject=?", (subject,)).fetchone()[0]
        if count >= max_facts:
            # drop the least-supported, oldest fact to make room
            self._conn.execute(
                "DELETE FROM facts WHERE id = ("
                "  SELECT id FROM facts WHERE subject=? ORDER BY support_count ASC, last_updated ASC LIMIT 1"
                ")", (subject,),
            )

    def facts_about(self, subject: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT subject, predicate, object, confidence, last_updated, support_count "
            "FROM facts WHERE subject=? ORDER BY confidence DESC", (subject,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "subject": row[0], "predicate": row[1], "object": row[2],
            "confidence": row[3], "last_updated": row[4], "support_count": row[5],
        }