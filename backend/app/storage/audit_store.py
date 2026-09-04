"""SQLite Audit Store for AML investigation queries, detection flags, and analyst feedback."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from app.core.config import settings
from app.models.schemas import ExecutionPlan, ExecutionTrace, Flag, RiskTier


def _get_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _parse_db_path(db_url_or_path: Optional[Union[str, Path]] = None) -> str:
    """Normalize database connection path from SQLite URL or filepath."""
    if db_url_or_path is None:
        db_url_or_path = settings.SQLITE_DB_URL

    path_str = str(db_url_or_path)
    if path_str.startswith("sqlite:///"):
        path_str = path_str.replace("sqlite:///", "", 1)

    if path_str == ":memory:":
        return ":memory:"

    target_path = Path(path_str).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return str(target_path)


class AuditStore:
    """Persistent SQLite store for AML investigation queries, flags, and feedback."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        self.db_path = _parse_db_path(db_path)
        self._is_memory = self.db_path == ":memory:"
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            # For in-memory databases, keep a persistent connection so tables persist
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a thread-safe SQLite connection with Row factory."""
        if self._is_memory and self._mem_conn is not None:
            yield self._mem_conn
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize database tables, indexes, and configure WAL journal mode."""
        with self.get_connection() as conn:
            if not self._is_memory:
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                except sqlite3.DatabaseError:
                    pass
            conn.execute("PRAGMA foreign_keys = ON;")

            # Table 1: audit_queries (logs search & investigation queries)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_queries (
                    id TEXT PRIMARY KEY,
                    query_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    detected_intent TEXT,
                    active_filters TEXT,
                    target_entities TEXT,
                    invoked_tools TEXT,
                    skipped_tools TEXT,
                    execution_time_ms REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'SUCCESS',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                );
            """)

            # Table 2: audit_flags (logs triggered AML rule flags & ML anomaly findings)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_flags (
                    id TEXT PRIMARY KEY,
                    flag_id TEXT NOT NULL UNIQUE,
                    query_id TEXT,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    rule_version TEXT DEFAULT 'v1.0',
                    severity TEXT NOT NULL,
                    entity_id TEXT,
                    transaction_ids TEXT,
                    typology TEXT,
                    reason TEXT NOT NULL,
                    evidence TEXT,
                    feedback_status TEXT DEFAULT 'PENDING',
                    analyst_notes TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Table 3: audit_feedback (logs compliance review feedback history)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_feedback (
                    id TEXT PRIMARY KEY,
                    flag_id TEXT NOT NULL,
                    query_id TEXT,
                    feedback_status TEXT NOT NULL,
                    analyst_id TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (flag_id) REFERENCES audit_flags (flag_id) ON DELETE CASCADE
                );
            """)

            # Indexes for fast lookup & filtering
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_query_id ON audit_queries(query_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_created_at ON audit_queries(created_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_flag_id ON audit_flags(flag_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_query_id ON audit_flags(query_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_entity_id ON audit_flags(entity_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_severity ON audit_flags(severity);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_rule_id ON audit_flags(rule_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flags_feedback ON audit_flags(feedback_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_flag_id ON audit_feedback(flag_id);")

            conn.commit()

    def log_query(
        self,
        query_text: str,
        query_id: Optional[str] = None,
        detected_intent: Optional[str] = None,
        active_filters: Optional[Dict[str, Any]] = None,
        target_entities: Optional[List[str]] = None,
        invoked_tools: Optional[List[str]] = None,
        skipped_tools: Optional[Union[List[Dict[str, Any]], List[Any]]] = None,
        execution_time_ms: float = 0.0,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[Union[str, datetime]] = None,
    ) -> str:
        """Record an investigation query execution trace."""
        record_id = str(uuid.uuid4())
        resolved_query_id = query_id or record_id

        if isinstance(created_at, datetime):
            timestamp_str = created_at.isoformat()
        elif isinstance(created_at, str):
            timestamp_str = created_at
        else:
            timestamp_str = _get_utc_iso()

        # Handle skipped tools serialization
        skipped_tools_data = []
        if skipped_tools:
            for item in skipped_tools:
                if hasattr(item, "model_dump"):
                    skipped_tools_data.append(item.model_dump())
                elif isinstance(item, dict):
                    skipped_tools_data.append(item)
                else:
                    skipped_tools_data.append(str(item))

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_queries (
                    id, query_id, query_text, detected_intent, active_filters,
                    target_entities, invoked_tools, skipped_tools, execution_time_ms,
                    status, error_message, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    resolved_query_id,
                    query_text,
                    detected_intent,
                    json.dumps(active_filters or {}),
                    json.dumps(target_entities or []),
                    json.dumps(invoked_tools or []),
                    json.dumps(skipped_tools_data),
                    float(execution_time_ms),
                    status,
                    error_message,
                    timestamp_str,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

        return resolved_query_id

    def log_execution_plan(self, plan: ExecutionPlan, execution_time_ms: float = 0.0) -> str:
        """Helper to log directly from a Pydantic ExecutionPlan."""
        return self.log_query(
            query_text=plan.query,
            query_id=plan.plan_id,
            detected_intent=plan.detected_intent,
            active_filters=plan.active_filters,
            target_entities=plan.target_entities,
            invoked_tools=plan.invoked_tools,
            skipped_tools=[tool.model_dump() for tool in plan.skipped_tools],
            execution_time_ms=execution_time_ms,
            status="SUCCESS",
            metadata={"reasoning": plan.reasoning} if plan.reasoning else {},
            created_at=plan.created_at,
        )

    def log_execution_trace(self, trace: ExecutionTrace, query_text: str = "") -> str:
        """Helper to log directly from a Pydantic ExecutionTrace."""
        return self.log_query(
            query_text=query_text or f"Trace {trace.trace_id}",
            query_id=trace.query_id or trace.trace_id,
            detected_intent=trace.detected_intent,
            active_filters=trace.active_filters,
            invoked_tools=trace.invoked_tools,
            skipped_tools=[tool.model_dump() for tool in trace.skipped_tools],
            execution_time_ms=trace.total_execution_time_ms,
            status=trace.status.value if hasattr(trace.status, "value") else str(trace.status),
            error_message=trace.error_message,
            metadata={"execution_timings_ms": trace.execution_timings_ms},
            created_at=trace.created_at,
        )

    def log_flags(
        self,
        flags: List[Union[Flag, Dict[str, Any]]],
        query_id: Optional[str] = None,
        rule_version: str = "v1.0",
    ) -> List[str]:
        """Insert a batch of AML detection flags into the audit store."""
        logged_flag_ids: List[str] = []
        if not flags:
            return logged_flag_ids

        records = []
        for flag in flags:
            record_id = str(uuid.uuid4())
            if isinstance(flag, Flag):
                flag_id = flag.flag_id
                rule_id = flag.rule_id
                rule_name = flag.rule_name
                severity = flag.severity.value if hasattr(flag.severity, "value") else str(flag.severity)
                entity_id = flag.entity_id
                tx_ids = json.dumps(flag.transaction_ids)
                typology = flag.typology
                reason = flag.reason
                evidence = json.dumps(flag.evidence)
                ts = flag.timestamp.isoformat() if isinstance(flag.timestamp, datetime) else str(flag.timestamp)
            elif isinstance(flag, dict):
                flag_id = flag.get("flag_id") or str(uuid.uuid4())
                rule_id = flag.get("rule_id", "UNKNOWN_RULE")
                rule_name = flag.get("rule_name", rule_id)
                severity_raw = flag.get("severity", "MEDIUM")
                severity = severity_raw.value if hasattr(severity_raw, "value") else str(severity_raw)
                entity_id = flag.get("entity_id")
                tx_ids = json.dumps(flag.get("transaction_ids", []))
                typology = flag.get("typology")
                reason = flag.get("reason", "")
                evidence = json.dumps(flag.get("evidence", {}))
                ts_raw = flag.get("timestamp")
                if isinstance(ts_raw, datetime):
                    ts = ts_raw.isoformat()
                elif isinstance(ts_raw, str):
                    ts = ts_raw
                else:
                    ts = _get_utc_iso()
            else:
                raise TypeError(f"Unsupported flag format: {type(flag)}")

            logged_flag_ids.append(flag_id)
            records.append((
                record_id,
                flag_id,
                query_id,
                rule_id,
                rule_name,
                rule_version,
                severity,
                entity_id,
                tx_ids,
                typology,
                reason,
                evidence,
                "PENDING",
                None,
                None,
                ts,
            ))

        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO audit_flags (
                    id, flag_id, query_id, rule_id, rule_name, rule_version,
                    severity, entity_id, transaction_ids, typology, reason,
                    evidence, feedback_status, analyst_notes, reviewed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()

        return logged_flag_ids

    def log_feedback(
        self,
        flag_id: str,
        feedback_status: str,
        analyst_id: str = "analyst_default",
        notes: str = "",
        query_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record analyst review feedback for a flag and update flag status."""
        feedback_id = str(uuid.uuid4())
        reviewed_at = _get_utc_iso()

        valid_statuses = {"CONFIRMED_SUSPICIOUS", "FALSE_POSITIVE", "DISMISSED", "UNDER_REVIEW", "PENDING"}
        normalized_status = feedback_status.upper()
        if normalized_status not in valid_statuses:
            normalized_status = feedback_status

        with self.get_connection() as conn:
            # Verify flag exists
            cursor = conn.execute("SELECT flag_id, query_id FROM audit_flags WHERE flag_id = ?", (flag_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Flag ID not found in audit store: {flag_id}")

            assoc_query_id = query_id or row["query_id"]

            # Update flag status
            conn.execute(
                """
                UPDATE audit_flags
                SET feedback_status = ?, analyst_notes = ?, reviewed_at = ?
                WHERE flag_id = ?
                """,
                (normalized_status, notes, reviewed_at, flag_id),
            )

            # Record feedback audit event
            conn.execute(
                """
                INSERT INTO audit_feedback (
                    id, flag_id, query_id, feedback_status, analyst_id, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback_id, flag_id, assoc_query_id, normalized_status, analyst_id, notes, reviewed_at),
            )
            conn.commit()

        return {
            "feedback_id": feedback_id,
            "flag_id": flag_id,
            "query_id": assoc_query_id,
            "feedback_status": normalized_status,
            "analyst_id": analyst_id,
            "notes": notes,
            "reviewed_at": reviewed_at,
        }

    def get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a logged query by query_id."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM audit_queries WHERE query_id = ? LIMIT 1", (query_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_query_dict(row)

    def get_queries(
        self,
        limit: int = 50,
        offset: int = 0,
        intent: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated list of logged queries."""
        query = "SELECT * FROM audit_queries WHERE 1=1"
        params: List[Any] = []

        if intent:
            query += " AND detected_intent = ?"
            params.append(intent)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_query_dict(row) for row in cursor.fetchall()]

    def get_flags(
        self,
        query_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        severity: Optional[Union[str, RiskTier]] = None,
        feedback_status: Optional[str] = None,
        rule_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve filtered and paginated AML detection flags."""
        query = "SELECT * FROM audit_flags WHERE 1=1"
        params: List[Any] = []

        if query_id:
            query += " AND query_id = ?"
            params.append(query_id)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if severity:
            sev_str = severity.value if hasattr(severity, "value") else str(severity)
            query += " AND severity = ?"
            params.append(sev_str)
        if feedback_status:
            query += " AND feedback_status = ?"
            params.append(feedback_status.upper())
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_flag_dict(row) for row in cursor.fetchall()]

    def get_flag(self, flag_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific flag and its feedback history by flag_id."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM audit_flags WHERE flag_id = ? LIMIT 1", (flag_id,))
            row = cursor.fetchone()
            if not row:
                return None
            flag_dict = self._row_to_flag_dict(row)

            # Attach feedback history
            cursor_fb = conn.execute(
                "SELECT * FROM audit_feedback WHERE flag_id = ? ORDER BY created_at ASC",
                (flag_id,),
            )
            flag_dict["feedback_history"] = [self._row_to_feedback_dict(fb_row) for fb_row in cursor_fb.fetchall()]
            return flag_dict

    def get_flag_feedback_history(self, flag_id: str) -> List[Dict[str, Any]]:
        """Get chronological audit history of feedback events for a flag."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_feedback WHERE flag_id = ? ORDER BY created_at ASC",
                (flag_id,),
            )
            return [self._row_to_feedback_dict(row) for row in cursor.fetchall()]

    def get_audit_summary(self) -> Dict[str, Any]:
        """Aggregate statistical summary of logged queries, flags, and analyst reviews."""
        with self.get_connection() as conn:
            total_queries = conn.execute("SELECT COUNT(*) FROM audit_queries").fetchone()[0]
            total_flags = conn.execute("SELECT COUNT(*) FROM audit_flags").fetchone()[0]
            total_feedback = conn.execute("SELECT COUNT(*) FROM audit_feedback").fetchone()[0]

            # Breakdown by severity
            sev_cursor = conn.execute("SELECT severity, COUNT(*) as cnt FROM audit_flags GROUP BY severity")
            severity_counts = {row["severity"]: row["cnt"] for row in sev_cursor.fetchall()}

            # Breakdown by feedback status
            fb_cursor = conn.execute("SELECT feedback_status, COUNT(*) as cnt FROM audit_flags GROUP BY feedback_status")
            feedback_counts = {row["feedback_status"]: row["cnt"] for row in fb_cursor.fetchall()}

            # Top triggered rules
            rule_cursor = conn.execute(
                "SELECT rule_id, rule_name, COUNT(*) as cnt FROM audit_flags GROUP BY rule_id ORDER BY cnt DESC LIMIT 5"
            )
            top_rules = [{"rule_id": r["rule_id"], "rule_name": r["rule_name"], "count": r["cnt"]} for r in rule_cursor.fetchall()]

        return {
            "total_queries": total_queries,
            "total_flags": total_flags,
            "total_feedback_events": total_feedback,
            "flags_by_severity": severity_counts,
            "flags_by_feedback_status": feedback_counts,
            "top_triggered_rules": top_rules,
        }

    # Serialization Helpers
    @staticmethod
    def _row_to_query_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "query_id": row["query_id"],
            "query_text": row["query_text"],
            "detected_intent": row["detected_intent"],
            "active_filters": json.loads(row["active_filters"] or "{}"),
            "target_entities": json.loads(row["target_entities"] or "[]"),
            "invoked_tools": json.loads(row["invoked_tools"] or "[]"),
            "skipped_tools": json.loads(row["skipped_tools"] or "[]"),
            "execution_time_ms": row["execution_time_ms"],
            "status": row["status"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    @staticmethod
    def _row_to_flag_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "flag_id": row["flag_id"],
            "query_id": row["query_id"],
            "rule_id": row["rule_id"],
            "rule_name": row["rule_name"],
            "rule_version": row["rule_version"],
            "severity": row["severity"],
            "entity_id": row["entity_id"],
            "transaction_ids": json.loads(row["transaction_ids"] or "[]"),
            "typology": row["typology"],
            "reason": row["reason"],
            "evidence": json.loads(row["evidence"] or "{}"),
            "feedback_status": row["feedback_status"],
            "analyst_notes": row["analyst_notes"],
            "reviewed_at": row["reviewed_at"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _row_to_feedback_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "flag_id": row["flag_id"],
            "query_id": row["query_id"],
            "feedback_status": row["feedback_status"],
            "analyst_id": row["analyst_id"],
            "notes": row["notes"],
            "created_at": row["created_at"],
        }


_global_audit_store: Optional[AuditStore] = None


def get_audit_store(db_path: Optional[Union[str, Path]] = None) -> AuditStore:
    """Get or create singleton AuditStore instance."""
    global _global_audit_store
    if db_path is not None:
        return AuditStore(db_path=db_path)

    if _global_audit_store is None:
        _global_audit_store = AuditStore()
        _global_audit_store.init_db()

    return _global_audit_store
