# adk_agent_app/services/firestore_memory_service.py
from datetime import datetime, timezone
import os
import re
from typing import Any

from google.adk.memory import BaseMemoryService, VertexAiMemoryBankService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.genai import types

from ..config import FIRESTORE_SESSION_DB, PROJECT_ID, logger


def _extract_words(text: str) -> set[str]:
    """Extracts lowercase alphanumeric tokens (length >= 3) for keyword/semantic matching."""
    return {w for w in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(w) >= 3}


class FirestoreMemoryService(BaseMemoryService):
    """Production Firestore implementation of ADK's `BaseMemoryService`.

    Persists completed conversation sessions as long-term memory entries inside the
    `sosta_memories` collection of `adk-agent-dev-session-memory-fs`, enabling instant
    cross-session recall across container restarts without external indexing latency.
    """

    def __init__(
        self,
        project: str | None = None,
        collection: str = "sosta_memories",
        database: str = FIRESTORE_SESSION_DB,
    ):
        self.project = project or PROJECT_ID
        self.collection_name = collection
        self.database = database
        self._db: firestore.AsyncClient | None = None

    @property
    def db(self) -> firestore.AsyncClient:
        if self._db is None:
            self._db = firestore.AsyncClient(
                project=self.project,
                database=self.database,
            )
        return self._db

    async def add_session_to_memory(self, session: Session) -> None:
        """Consolidates a Session's conversational events into Firestore long-term memory."""
        entries: list[dict[str, Any]] = []
        for event in session.events:
            if not event.content or not event.content.parts:
                continue
            text_parts = [
                part.text
                for part in event.content.parts
                if hasattr(part, "text") and part.text
            ]
            if not text_parts:
                continue

            combined_text = " ".join(text_parts).strip()
            if not combined_text:
                continue

            iso_ts = (
                datetime.fromtimestamp(event.timestamp, tz=timezone.utc).isoformat()
                if event.timestamp
                else datetime.now(tz=timezone.utc).isoformat()
            )
            entries.append(
                {
                    "event_id": event.id or "",
                    "author": event.author or "user",
                    "role": event.content.role or "user",
                    "text": combined_text,
                    "timestamp": iso_ts,
                }
            )

        doc_ref = self.db.collection(self.collection_name).document(session.id)
        await doc_ref.set(
            {
                "appName": session.app_name,
                "userId": session.user_id,
                "sessionId": session.id,
                "updatedAt": datetime.now(tz=timezone.utc).isoformat(),
                "entries": entries,
            }
        )
        logger.info(
            f"Saved {len(entries)} memory entries from session '{session.id}' "
            f"for user '{session.user_id}' into Firestore ({self.database}/{self.collection_name})."
        )

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """Searches stored user memories in Firestore and returns matching `MemoryEntry` items."""
        query_ref = (
            self.db.collection(self.collection_name)
            .where(filter=FieldFilter("appName", "==", app_name))
            .where(filter=FieldFilter("userId", "==", user_id))
        )
        docs = await query_ref.get()
        query_words = _extract_words(query)

        scored_memories: list[tuple[int, MemoryEntry]] = []
        all_user_memories: list[MemoryEntry] = []

        for doc in docs:
            data = doc.to_dict() or {}
            for entry in data.get("entries", []):
                text = entry.get("text", "")
                if not text:
                    continue
                mem_entry = MemoryEntry(
                    id=entry.get("event_id") or doc.id,
                    author=entry.get("author", "user"),
                    timestamp=entry.get("timestamp"),
                    content=types.Content(
                        role=entry.get("role", "user"),
                        parts=[types.Part.from_text(text=text)],
                    ),
                )
                all_user_memories.append(mem_entry)
                entry_words = _extract_words(text)
                overlap = len(query_words & entry_words)
                if overlap > 0:
                    scored_memories.append((overlap, mem_entry))

        if scored_memories:
            scored_memories.sort(key=lambda item: item[0], reverse=True)
            return SearchMemoryResponse(
                memories=[item[1] for item in scored_memories[:5]]
            )

        # Fallback: return the most recent memories for this user so preload_memory
        # provides prior trip context even when the user's greeting is short.
        return SearchMemoryResponse(memories=all_user_memories[-5:])


def create_memory_service(
    use_vertex_memory_bank: bool = False,
) -> BaseMemoryService:
    """Factory that returns either `VertexAiMemoryBankService` (if configured) or `FirestoreMemoryService`."""
    agent_engine_id = os.getenv("VERTEX_MEMORY_BANK_AGENT_ENGINE_ID")
    if use_vertex_memory_bank and agent_engine_id:
        logger.info(
            f"Initializing VertexAiMemoryBankService (agent_engine_id={agent_engine_id})"
        )
        return VertexAiMemoryBankService(agent_engine_id=agent_engine_id)

    logger.info(
        f"Initializing FirestoreMemoryService (database={FIRESTORE_SESSION_DB}, collection=sosta_memories)"
    )
    return FirestoreMemoryService(
        project=PROJECT_ID,
        database=FIRESTORE_SESSION_DB,
    )
