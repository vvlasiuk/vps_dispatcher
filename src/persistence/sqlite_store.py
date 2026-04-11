from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from contracts.workflow_state import IdentityHints, MessageJournalEntry, WorkflowState


class SQLiteStateStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self._db_path) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_states (
                    conversation_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    group_id TEXT,
                    algorithm TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    related_document_id TEXT,
                    last_message_id TEXT,
                    identity_hints_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (conversation_id, case_id)
                )
                """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS message_journal (
                    event_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await connection.commit()

    async def get_active_state(
        self,
        *,
        source_system: str,
        source_id: str,
        chat_id: str,
    ) -> WorkflowState | None:
        async with aiosqlite.connect(self._db_path) as connection:
            connection.row_factory = aiosqlite.Row
            cursor = await connection.execute(
                """
                SELECT *
                FROM workflow_states
                WHERE source_system = ?
                  AND source_id = ?
                  AND chat_id = ?
                  AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (source_system, source_id, chat_id),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_state(row)

    async def upsert_state(self, state: WorkflowState) -> None:
        async with aiosqlite.connect(self._db_path) as connection:
            await connection.execute(
                """
                INSERT INTO workflow_states (
                    conversation_id,
                    case_id,
                    source_system,
                    source_id,
                    chat_id,
                    group_id,
                    algorithm,
                    stage,
                    status,
                    related_document_id,
                    last_message_id,
                    identity_hints_json,
                    metadata_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id, case_id) DO UPDATE SET
                    algorithm = excluded.algorithm,
                    stage = excluded.stage,
                    status = excluded.status,
                    related_document_id = excluded.related_document_id,
                    last_message_id = excluded.last_message_id,
                    identity_hints_json = excluded.identity_hints_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.conversation_id,
                    state.case_id,
                    state.source_system,
                    state.source_id,
                    state.chat_id,
                    state.group_id,
                    state.algorithm.value,
                    state.stage.value,
                    state.status.value,
                    state.related_document_id,
                    state.last_message_id,
                    state.identity_hints.model_dump_json(),
                    json.dumps(state.metadata, ensure_ascii=True),
                    state.created_at.isoformat(),
                    state.updated_at.isoformat(),
                ),
            )
            await connection.commit()

    async def append_journal(self, entry: MessageJournalEntry) -> None:
        async with aiosqlite.connect(self._db_path) as connection:
            await connection.execute(
                """
                INSERT INTO message_journal (
                    event_id,
                    conversation_id,
                    case_id,
                    message_id,
                    event_type,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.event_id,
                    entry.conversation_id,
                    entry.case_id,
                    entry.message_id,
                    entry.event_type,
                    json.dumps(entry.payload, ensure_ascii=True),
                    entry.created_at.isoformat(),
                ),
            )
            await connection.commit()

    async def mark_case_completed(self, conversation_id: str, case_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as connection:
            await connection.execute(
                """
                UPDATE workflow_states
                SET status = 'completed', updated_at = ?
                WHERE conversation_id = ? AND case_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), conversation_id, case_id),
            )
            await connection.commit()

    def _row_to_state(self, row: aiosqlite.Row) -> WorkflowState:
        return WorkflowState(
            conversation_id=row["conversation_id"],
            case_id=row["case_id"],
            source_system=row["source_system"],
            source_id=row["source_id"],
            chat_id=row["chat_id"],
            group_id=row["group_id"],
            algorithm=row["algorithm"],
            stage=row["stage"],
            status=row["status"],
            related_document_id=row["related_document_id"],
            last_message_id=row["last_message_id"],
            identity_hints=IdentityHints.model_validate_json(row["identity_hints_json"]),
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
