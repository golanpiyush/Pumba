"""
memory/db_entities.py

Tracks named entities in the household — primarily the bird and dog, but
open-ended (could later include a specific toy, a recurring visitor not
yet in people/profiles.yaml, etc.). This is deliberately separate from
db_people.py (which is for humans with voiceprints/relationships) and
db_semantic.py (which is for beliefs ABOUT a subject, not the subject's
own identity record).

The critical feature: an entity can exist as an incomplete STUB before
it's fully named. "I got a bird" creates a stub entity (kind="bird",
name=None, acquired_at=<timestamp>). "Her name is Ken" — said days later —
doesn't create a new entity, it fills in the name slot on the existing
stub, while preserving acquired_at as it originally was. This mirrors how
a real memory works: you don't relearn when you got the bird just because
you learned its name later; the two facts merge onto one timeline.

Inputs: entity dicts / partial updates (kind, name, acquired_at, notes).
Outputs: query methods used by brain/entity_resolver.py to look up
         candidates, and by prompt_builder.py to give the LLM accurate
         "here's what I actually know and when I learned it" context.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class EntitiesDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["entities"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,             -- "bird" | "dog" | "unknown"
                name TEXT,                       -- NULL until named
                acquired_at REAL,                -- when we first learned this entity exists
                named_at REAL,                    -- when the name slot was filled (may be much later)
                last_referenced_at REAL NOT NULL,
                notes TEXT
            )
        """)
        self._conn.commit()

    def create_stub(self, kind: str, acquired_at: Optional[float] = None) -> int:
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO entities (kind, name, acquired_at, named_at, last_referenced_at, notes) "
            "VALUES (?, NULL, ?, NULL, ?, '')",
            (kind, acquired_at or now, now),
        )
        self._conn.commit()
        return cur.lastrowid

    def set_name(self, entity_id: int, name: str) -> None:
        self._conn.execute(
            "UPDATE entities SET name=?, named_at=?, last_referenced_at=? WHERE id=?",
            (name, time.time(), time.time(), entity_id),
        )
        self._conn.commit()

    def touch(self, entity_id: int) -> None:
        self._conn.execute(
            "UPDATE entities SET last_referenced_at=? WHERE id=?", (time.time(), entity_id)
        )
        self._conn.commit()

    def find_unnamed_stub(self, kind: str) -> Optional[Dict[str, Any]]:
        """The most recent unnamed entity of a given kind — used when a name
        arrives with no other context, to find what it's probably naming."""
        row = self._conn.execute(
            "SELECT id, kind, name, acquired_at, named_at, last_referenced_at, notes "
            "FROM entities WHERE kind=? AND name IS NULL ORDER BY acquired_at DESC LIMIT 1",
            (kind,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT id, kind, name, acquired_at, named_at, last_referenced_at, notes "
            "FROM entities WHERE LOWER(name)=?",
            (name.lower(),),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def all_entities(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, kind, name, acquired_at, named_at, last_referenced_at, notes FROM entities"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0], "kind": row[1], "name": row[2], "acquired_at": row[3],
            "named_at": row[4], "last_referenced_at": row[5], "notes": row[6],
        }