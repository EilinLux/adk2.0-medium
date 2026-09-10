"""
ADK 2.0 101 - Article 3b: Session Service Demo
----------------------------------------------
WARNING: Ypu must have a valid Google Cloud Project with Firestore enabled to run this demo. 
In this case the code is available in the terraform folder that is present in the adk2.0-medium repo from branch 04-gcp-setup. 
Please follow the instructions in the README.md file to set up your GCP project and Firestore database before running this demo.

This script demonstrates the complete SessionService lifecycle in Google ADK:
1. Creating & Seeding sessions across state scopes (app:, user:, plain, temp:)
2. Writing to live session state inside custom tools using `ToolContext`
3. Dynamically injecting state variables into agent prompt templates
4. Updating state mid-pipeline via append_event with state_delta
5. Switching between InMemorySessionService, DatabaseSessionService, and FirestoreSessionService
"""

import asyncio
import logging
import os
import re
import time
from functools import wraps
from typing import Any, Dict
import warnings
# Suppress experimental warnings and deprecation notices
warnings.filterwarnings("ignore", message=".*JSON_SCHEMA_FOR_FUNC_DECL.*")
warnings.filterwarnings(
    "ignore", 
    category=FutureWarning, 
    module="google.adk.memory.vertex_ai_memory_bank_service"
)


from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Import Google ADK primitives
from google.adk.agents import Agent
from google.adk.events import Event, EventActions
from google.adk.events.event import Event as ADKEvent
from google.adk.platform import uuid as platform_uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, _session_util
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.tools import ToolContext

# Import Google Cloud Firestore drivers and core exception wrappers
from google.api_core import exceptions as google_exceptions
from google.cloud import firestore
from google.genai import types

load_dotenv()

# Configure module-level logger
logger = logging.getLogger(__name__)

# Storage constants
STORAGE_VERSION = 2  # Subcollection layout for events (sessions/{session_id}/events)
EVENTS_SUBCOLLECTION = "events"
SESSION_DB_NAME = "adk-agent-dev-session-memory-fs"

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
    """
    Custom Firestore Session Service implementation of ADK's `BaseSessionService`.
    Manages session creation, retrieval, updates, and deletion in Google Cloud Firestore.
    """

    def __init__(
        self,
        project: str | None = None,
        collection: str = "sosta_sessions",
        database: str = SESSION_DB_NAME,  # Updated default to SESSION_DB_NAME
    ):
        """
        Initializes configuration parameters for the Firestore backend.
        
        Args:
            project: Google Cloud Project ID (falls back to GOOGLE_CLOUD_PROJECT env var).
            collection: Target Firestore root collection name (defaults to "sosta_sessions").
            database: Firestore database instance name (defaults to SESSION_DB_NAME).
        """
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if not self.project:
            raise ValueError(
                "GCP Project ID must be provided or set via GOOGLE_CLOUD_PROJECT environment variable."
            )       
        self.collection_name = collection
        self.database = database
        self._db: firestore.AsyncClient | None = None

    @property
    def db(self) -> firestore.AsyncClient:
        """Lazily initializes and returns the async Firestore client (`firestore.AsyncClient`)."""
        if self._db is None:
            logger.info(
                "Creating Firestore AsyncClient with project='%s', database='%s'",
                self.project,
                self.database,
            )
            self._db = firestore.AsyncClient(
                project=self.project,
                database=self.database,
            )
        return self._db

    def _session_doc_ref(self, session_id: str) -> firestore.AsyncDocumentReference:
        """Helper to return a DocumentReference for a root session document (`sessions/{session_id}`)."""
        return self.db.collection(self.collection_name).document(session_id)

    def _events_collection_ref(
        self,
        session_id: str,
    ) -> firestore.AsyncCollectionReference:
        """Helper to return a CollectionReference for events subcollection (`sessions/{session_id}/events`)."""
        return self._session_doc_ref(session_id).collection(EVENTS_SUBCOLLECTION)

    async def _upsert_event_if_needed(self, *, session_id: str, event: ADKEvent) -> bool:
        """Upserts an Event into the subcollection if it doesn't exist or has changed."""
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
        """Fetches, filters, and orders event payloads from the session's Firestore subcollection."""
        query: firestore.AsyncQuery = self._events_collection_ref(session_id)

        if config and config.after_timestamp is not None:
            query = query.where("timestamp", ">=", config.after_timestamp)

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

        # FIX: Use state directly or flatten all state_deltas so scope prefixes survive
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
        """Retrieves a session document from Firestore and hydrates nested event history."""
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
            session = Session.model_validate(session_payload)
            return session

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
        """Lists lightweight session summaries (metadata only) for an application/user."""
        query = (
            self.db.collection(self.collection_name)
            .where("appName", "==", app_name)
            .select(["id", "appName", "userId", "state", "lastUpdateTime"])
        )
        if user_id:
            query = query.where("userId", "==", user_id)

        docs = await query.get()
        sessions_list = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                data["events"] = []
                sessions_list.append(Session.model_validate(data))

        return ListSessionsResponse(sessions=sessions_list)

    @handle_firestore_errors
    async def list_sessions_extended(
        self,
        *,
        app_name: str,
        user_id: str | None = None,
    ) -> ListSessionsResponse:
        """Lists sessions and fully hydrates all nested event records from subcollections."""
        query = self.db.collection(self.collection_name).where(
            "appName",
            "==",
            app_name,
        )
        if user_id:
            query = query.where("userId", "==", user_id)

        docs = await query.get()
        sessions_list = []
        for doc in docs:
            data = doc.to_dict()
            if not data:
                continue

            if data.get("storageVersion") == STORAGE_VERSION:
                event_payloads = await self._load_event_payloads(session_id=doc.id)
                session_payload = {**data, "events": event_payloads}
                session_payload.pop("storageVersion", None)
                sessions_list.append(Session.model_validate(session_payload))
            else:
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
        """
        Deletes a target session document and all nested events from Firestore
        after validating tenant ownership.
        """
        session_ref = self.db.collection(self.collection_name).document(session_id)
        doc = await session_ref.get()

        if not doc.exists:
            return

        data = doc.to_dict() or {}

        # 1. Tenant Isolation Guard: Verify ownership before deleting
        if data.get("appName") != app_name or data.get("userId") != user_id:
            logger.warning(
                f"Unauthorized delete attempt for session {session_id}. "
                f"Expected {app_name}/{user_id}, got {data.get('appName')}/{data.get('userId')}"
            )
            return

        # 2. Delete all nested event documents in the 'events' subcollection
        events_ref = session_ref.collection(EVENTS_SUBCOLLECTION)
        event_docs = await events_ref.select([]).get()  # Fetch IDs only for performance

        if event_docs:
            batch = self.db.batch()
            for event_doc in event_docs:
                batch.delete(event_doc.reference)
            await batch.commit()  # Atomically purge subcollection

        # 3. Delete the root session document
        await session_ref.delete()
        logger.info(f"Successfully purged session '{session_id}' and all associated events.")
    @handle_firestore_errors
    async def append_event(self, session: Session, event: ADKEvent) -> ADKEvent:
        """Appends a new Event to the session, updates modified timestamp, and persists state."""
        if event.partial:
            return event

        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp

        await self._upsert_event_if_needed(session_id=session.id, event=event)

        await self._session_doc_ref(session.id).set(
            _sanitize_for_firestore(
                {
                    "state": session.state,
                    "lastUpdateTime": session.last_update_time,
                    "storageVersion": STORAGE_VERSION,
                },
            ),
            merge=True,
        )

        return event


# ============================================================================
# 1. Structured Schemas & Custom Tools
# ============================================================================

class PreferenceExtraction(BaseModel):
    favorite_dish: str = Field(
        description="The user's favorite dish or food preference extracted from text."
    )


async def search_restaurant_api(cuisine: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Mock external restaurant API tool. Stores metadata in temp: scope."""
    tool_context.session.state["temp:raw_api_payload"] = {
        "status_code": 200,
        "query_cuisine": cuisine,
        "results_count": 3,
        "raw_response_bytes": "0x4150495f5241575f44415441",
    }

    return {
        "status": "success",
        "message": f"Found 3 top-rated restaurants matching '{cuisine}'.",
    }


# ============================================================================
# 2. Agent Definitions & State Injection
# ============================================================================

gatekeeper_agent = Agent(
    name="gatekeeper_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a welcoming assistant for sosta_app. 
    Whenever a user mentions a food preference or favorite dish, 
    extract it cleanly using the response schema.
    """,
    output_key="user_information",
    output_schema=PreferenceExtraction,
)

concierge_agent = Agent(
    name="concierge_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a dining concierge for sosta_app.

    USER PROFILE:
    - Language: {user:user_preferred_language}
    - Dietary: {user:dietary_restrictions}

    SESSION CONTEXT:
    - Extracted Info: {user_information?}
    - Active Step: {workflow_step?}

    Respond in the user's preferred language ({user:user_preferred_language}), 
    acknowledge their dietary restriction ({user:dietary_restrictions}), 
    and use the 'search_restaurant_api' tool to find matching restaurants.
    """,
    tools=[search_restaurant_api],
)


# ============================================================================
# 3. Main Session Lifecycle Execution Loop
# ============================================================================

async def main():
    APP_NAME = "sosta_app"
    USER_ID = "user_zelda"
    SESSION_ID = "zelda_session_101"

    print("============================================================")
    print("🚀 1. INITIALIZING SESSION SERVICE & SEEDING STATE")
    print("============================================================")

    # Initialize FirestoreSessionService using default SESSION_DB_NAME
    session_service = FirestoreSessionService(
        collection="sosta_sessions",
        database=SESSION_DB_NAME,
    )

    global_app_config = {
        "app:enable_beta_recommendations": True,
        "app:system_version": "2.1.0",
    }

    # 1. CREATE & SEED SESSION
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={
            **global_app_config,
            "user:user_preferred_language": "Italian",   # Permanent User Scope
            "user:dietary_restrictions": "Vegetarian",  # Permanent User Scope
            "current_subagent": "gatekeeper_agent",     # Session Scope
            "workflow_step": "preference_collection",   # Session Scope
        },
    )

    print(f"Created Session: {session.id} for User: {session.user_id}")
    print("Initial State:", session.state)

    print("\n============================================================")
    print("🔄 2. MID-PIPELINE STATE PATCH (append_event with state_delta)")
    print("============================================================")

    # 2. UPDATE SESSION STATE VIA EVENT DELTA
    event = Event(
        author="system",
        actions=EventActions(state_delta={"workflow_step": "concierge_recommendation"}),
    )
    await session_service.append_event(session=session, event=event)

    updated_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("Updated Workflow Step:", updated_session.state.get("workflow_step"))

    print("\n============================================================")
    print("🤖 3. EXECUTING AGENT TURN WITH TOOLCONTEXT & INJECTION")
    print("============================================================")

    # Initialize Runner with SessionService
    runner = Runner(
        agent=concierge_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Construct a valid Content object
    query_text = "Can you find a good place for dinner tonight?"
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query_text)]
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content:
            part = event.content.parts[0]
            if hasattr(part, "text") and part.text:
                print(f"Agent Response:\n{part.text}\n")

    print("============================================================")
    print("📖 4. READING FINAL STATE & INSPECTING SCOPES")
    print("============================================================")

    # 3. READ SESSION STATE POST-RUN
    final_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print("Final State Keys & Values:")
    print(f"- User Language (user:): {final_session.state.get('user:user_preferred_language')}")
    print(f"- App Version (app:):   {final_session.state.get('app:system_version')}")
    print(f"- Workflow Step (plain): {final_session.state.get('workflow_step')}")
    print(f"- Ephemeral Payload (temp:): {final_session.state.get('temp:raw_api_payload')}")

    print("\n============================================================")
    print("🧹 5. EVICTING SESSION (DELETE)")
    print("============================================================")

    # 4. DELETE SESSION
    await session_service.delete_session(        
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID 
    )
    print(f"Session '{SESSION_ID}' successfully deleted from storage backend.")


if __name__ == "__main__":
    asyncio.run(main())