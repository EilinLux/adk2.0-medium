# adk_agent_app/services/firestore_session_service.py
from functools import wraps
import re
import time
from typing import Any

from google.adk.events.event import Event as ADKEvent
from google.adk.platform import uuid as platform_uuid
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.api_core import exceptions as google_exceptions
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..config import FIRESTORE_SESSION_DB, PROJECT_ID, logger

STORAGE_VERSION = 2  # Subcollection layout for events (sosta_sessions/{session_id}/events)
EVENTS_SUBCOLLECTION = "events"

# Regex pattern matching Firestore-reserved dunder keys (e.g., __internal__)
_RESERVED_KEY_RE = re.compile(r"^__.*__$")


def _sanitize_for_firestore(value: Any) -> Any:
    """Recursively strips Firestore-reserved dunder keys (__key__) from dictionaries and lists."""
    if isinstance(value, dict):
        return {
            k: _sanitize_for_firestore(v)
            for k, v in value.items()
            if not _RESERVED_KEY_RE.match(k)
        }
    if isinstance(value, list):
        return [_sanitize_for_firestore(item) for item in value]
    return value


def handle_firestore_errors(func):
    """Decorator to catch Firestore API exceptions and prevent unhandled crashes."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"Firestore API error in {func.__name__}: {e}")
            raise RuntimeError(f"Session service operation failed: {e}") from e
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise

    return wrapper


class FirestoreSessionService(BaseSessionService):
    """Production Firestore implementation of ADK's `BaseSessionService`.

    Persists active `Session` documents and nested `Event` subcollections inside
    the dedicated `adk-agent-dev-session-memory-fs` Firestore database so that
    multi-turn conversations and `user:` / `session` state survive container restarts.
    """

    def __init__(
        self,
        project: str | None = None,
        collection: str = "sosta_sessions",
        database: str = FIRESTORE_SESSION_DB,
    ):
        self.project = project or PROJECT_ID
        self.collection_name = collection
        self.database = database
        self._db: firestore.AsyncClient | None = None

    @property
    def db(self) -> firestore.AsyncClient:
        """Lazily initializes and returns the async Firestore client (`firestore.AsyncClient`)."""
        if self._db is None:
            self._db = firestore.AsyncClient(
                project=self.project,
                database=self.database,
            )
        return self._db

    def _session_doc_ref(self, session_id: str) -> firestore.AsyncDocumentReference:
        return self.db.collection(self.collection_name).document(session_id)

    def _events_collection_ref(
        self,
        session_id: str,
    ) -> firestore.AsyncCollectionReference:
        return self._session_doc_ref(session_id).collection(EVENTS_SUBCOLLECTION)

    async def _upsert_event_if_needed(
        self, *, session_id: str, event: ADKEvent
    ) -> bool:
        event_id = (event.id or "").strip() or platform_uuid.new_uuid()
        event_payload = _sanitize_for_firestore(event.model_dump(by_alias=True))
        event_doc_ref = self._events_collection_ref(session_id).document(event_id)
        existing_doc = await event_doc_ref.get()

        if existing_doc.exists and existing_doc.to_dict() == event_payload:
            return False

        await event_doc_ref.set(event_payload)
        return True

    async def _load_event_payloads(
        self,
        *,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> list[dict[str, Any]]:
        query: firestore.AsyncQuery = self._events_collection_ref(session_id)

        if config and config.after_timestamp is not None:
            query = query.where(
                filter=FieldFilter("timestamp", ">=", config.after_timestamp)
            )

        has_recent_limit = bool(config and config.num_recent_events)
        if has_recent_limit:
            query = query.order_by(
                "timestamp",
                direction=firestore.Query.DESCENDING,
            ).limit(config.num_recent_events)
        else:
            query = query.order_by("timestamp")

        docs = await query.get()
        events = [doc.to_dict() for doc in docs if doc.to_dict()]

        events.sort(
            key=lambda event: (event.get("timestamp", 0.0), str(event.get("id", ""))),
        )
        return events

    @handle_firestore_errors
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        session_id = (
            session_id.strip()
            if session_id and session_id.strip()
            else platform_uuid.new_uuid()
        )
        session_state = state or {}

        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=session_state,
            last_update_time=time.time(),
        )

        session_payload = session.model_dump(by_alias=True, exclude={"events"})
        session_payload["storageVersion"] = STORAGE_VERSION

        await self._session_doc_ref(session_id).set(
            _sanitize_for_firestore(session_payload),
        )
        return session

    @handle_firestore_errors
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        doc = await self._session_doc_ref(session_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        if data is None:
            return None

        if data.get("appName") != app_name or data.get("userId") != user_id:
            logger.warning(
                f"Session {session_id} found but app/user mismatch. "
                f"Expected {app_name}/{user_id}, got {data.get('appName')}/{data.get('userId')}",
            )
            return None

        if data.get("storageVersion") == STORAGE_VERSION:
            event_payloads = await self._load_event_payloads(
                session_id=session_id,
                config=config,
            )
            session_payload = {**data, "events": event_payloads}
            session_payload.pop("storageVersion", None)
            return Session.model_validate(session_payload)

        session = Session.model_validate(data)
        if config:
            if config.num_recent_events:
                session.events = session.events[-config.num_recent_events :]
            if config.after_timestamp:
                session.events = [
                    e for e in session.events if e.timestamp >= config.after_timestamp
                ]
        return session

    @handle_firestore_errors
    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: str | None = None,
    ) -> ListSessionsResponse:
        query = (
            self.db.collection(self.collection_name)
            .where(filter=FieldFilter("appName", "==", app_name))
            .select(["id", "appName", "userId", "state", "lastUpdateTime"])
        )
        if user_id:
            query = query.where(filter=FieldFilter("userId", "==", user_id))

        docs = await query.get()
        sessions_list = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                data["events"] = []
                sessions_list.append(Session.model_validate(data))

        return ListSessionsResponse(sessions=sessions_list)

    @handle_firestore_errors
    async def delete_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        session_ref = self._session_doc_ref(session_id)
        doc = await session_ref.get()
        if not doc.exists:
            return

        data = doc.to_dict() or {}
        if data.get("appName") != app_name or data.get("userId") != user_id:
            logger.warning(
                f"Unauthorized delete attempt for session {session_id}. "
                f"Expected {app_name}/{user_id}, got {data.get('appName')}/{data.get('userId')}"
            )
            return

        events_ref = session_ref.collection(EVENTS_SUBCOLLECTION)
        event_docs = await events_ref.select([]).get()
        if event_docs:
            batch = self.db.batch()
            for event_doc in event_docs:
                batch.delete(event_doc.reference)
            await batch.commit()

        await session_ref.delete()
        logger.info(
            f"Successfully purged session '{session_id}' and all associated events."
        )

    @handle_firestore_errors
    async def append_event(self, session: Session, event: ADKEvent) -> ADKEvent:
        if event.partial:
            return event

        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp

        await self._upsert_event_if_needed(session_id=session.id, event=event)

        # Strip ephemeral temp: keys before persisting state to Firestore
        persistent_state = {
            k: v for k, v in session.state.items() if not str(k).startswith("temp:")
        }

        await self._session_doc_ref(session.id).set(
            _sanitize_for_firestore(
                {
                    "state": persistent_state,
                    "lastUpdateTime": session.last_update_time,
                    "storageVersion": STORAGE_VERSION,
                },
            ),
            merge=True,
        )
        return event
