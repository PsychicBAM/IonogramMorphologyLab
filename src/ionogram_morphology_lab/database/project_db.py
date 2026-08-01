"""SQLite project metadata — large matrices are never stored here."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ProjectDatabase:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    config_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS frame_results (
                    frame_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    auto_json TEXT NOT NULL,
                    human_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    event TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                );
                """
            )

    def insert_project(self, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects(project_id, payload_json) VALUES (?,?)",
                (payload["project_id"], json.dumps(payload, ensure_ascii=False)),
            )

    def insert_run(self, run_id: str, project_id: str, created_at: str, config: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, project_id, created_at, config_json) VALUES (?,?,?,?)",
                (run_id, project_id, created_at, json.dumps(config, ensure_ascii=False)),
            )

    def insert_frame_result(
        self,
        frame_id: str,
        run_id: str,
        auto_result: dict[str, Any],
        created_at: str,
        human_result: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO frame_results(frame_id, run_id, auto_json, human_json, created_at) VALUES (?,?,?,?,?)",
                (
                    frame_id,
                    run_id,
                    json.dumps(auto_result, ensure_ascii=False),
                    json.dumps(human_result, ensure_ascii=False) if human_result else None,
                    created_at,
                ),
            )

    def update_human_decision(self, frame_id: str, human_result: dict[str, Any]) -> None:
        """Store human decision separately — never overwrite auto_json."""
        with self.connect() as conn:
            conn.execute(
                "UPDATE frame_results SET human_json=? WHERE frame_id=?",
                (json.dumps(human_result, ensure_ascii=False), frame_id),
            )

    def append_audit(self, ts: str, event: str, detail: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(ts, event, detail_json) VALUES (?,?,?)",
                (ts, event, json.dumps(detail, ensure_ascii=False)),
            )

    def list_frame_results(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT frame_id, auto_json, human_json, created_at FROM frame_results WHERE run_id=?",
                (run_id,),
            ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "frame_id": r["frame_id"],
                    "auto": json.loads(r["auto_json"]),
                    "human": json.loads(r["human_json"]) if r["human_json"] else None,
                    "created_at": r["created_at"],
                }
            )
        return out
