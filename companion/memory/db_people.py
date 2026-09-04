"""
memory/db_people.py

Per-person memory and profile store — distinct from db_semantic.py's
generic subject/predicate/object facts because people need richer,
relationship-specific fields: recognized voiceprint reference, preferred
tone (config: voice.tts.per_person_voice_overrides_key), running
relationship notes, and a link out to prompts/people/<key>.md for the
personality layer's per-person tone.

Seeded at first run from people/profiles.yaml; grows over time as
voice/speaker_id.py enrolls new voiceprints and memory_manager.py notices
recurring interaction patterns with a given person.

Inputs: person dicts keyed by a stable person_key (e.g. "nigam").
Outputs: query/update methods used by voice/speaker_id.py and
         brain/prompt_builder.py.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class PeopleDB:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory"]["people"]
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        Path(self.cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cfg["db_path"], check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS people (
                person_key TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                relationship TEXT NOT NULL,
                voiceprint_path TEXT,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                interaction_count INTEGER NOT NULL DEFAULT 0,
                notes TEXT
            )
        """)
        self._conn.commit()

    def upsert_person(self, person_key: str, display_name: str, relationship: str,
                       voiceprint_path: Optional[str] = None) -> None:
        now = time.time()
        existing = self._conn.execute("SELECT person_key FROM people WHERE person_key=?", (person_key,)).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE people SET last_seen=?, interaction_count=interaction_count+1 WHERE person_key=?",
                (now, person_key),
            )
        else:
            self._conn.execute(
                "INSERT INTO people (person_key, display_name, relationship, voiceprint_path, "
                "first_seen, last_seen, interaction_count, notes) VALUES (?, ?, ?, ?, ?, ?, 1, '')",
                (person_key, display_name, relationship, voiceprint_path, now, now),
            )
        self._conn.commit()

    def get_person(self, person_key: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT person_key, display_name, relationship, voiceprint_path, first_seen, last_seen, "
            "interaction_count, notes FROM people WHERE person_key=?", (person_key,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def all_people(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT person_key, display_name, relationship, voiceprint_path, first_seen, last_seen, "
            "interaction_count, notes FROM people"
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def append_note(self, person_key: str, note: str) -> None:
        person = self.get_person(person_key)
        if not person:
            return
        updated_notes = f"{person['notes']}\n{note}".strip()
        self._conn.execute("UPDATE people SET notes=? WHERE person_key=?", (updated_notes, person_key))
        self._conn.commit()

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "person_key": row[0], "display_name": row[1], "relationship": row[2],
            "voiceprint_path": row[3], "first_seen": row[4], "last_seen": row[5],
            "interaction_count": row[6], "notes": row[7],
        }