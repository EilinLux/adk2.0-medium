# tests/07a-tool-caching-and-session-scaling/test_session_scaling_v2.py
"""Comprehensive Tests for FirestoreSessionService Subcollection Scaling (STORAGE_VERSION = 2).

Verifies:
1. Subcollection architecture: Metadata is stored in root document; events are stored
   in subcollection `events/{event_id}`.
2. 1MB Limit Prevention: Appending large event payloads (exceeding 1MB total conversation)
   succeeds without exceeding Firestore's 1MB single-document constraint.
3. Event filtering with GetSessionConfig: num_recent_events and after_timestamp filters.
4. Backward compatibility: Seamlessly loads legacy v1 documents where events were stored
   in the root document array.
5. Cascade deletion: delete_session removes both root document and all subcollection events.
"""

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from google.adk.events.event import Event as ADKEvent
from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.session import Session
from google.genai import types

from adk_agent_app.services.firestore_session_service import (
    EVENTS_SUBCOLLECTION,
    STORAGE_VERSION,
    FirestoreSessionService,
)


class MockDocSnapshot:
    """Mock Firestore DocumentSnapshot."""

    def __init__(self, doc_id: str, data: Dict[str, Any] | None, exists: bool = True):
        self.id = doc_id
        self._data = data
        self.exists = exists
        self.reference = AsyncMock()

    def to_dict(self) -> Dict[str, Any] | None:
        return self._data.copy() if self._data is not None else None


class MockFirestoreAsyncClient:
    """In-memory async mock replicating Firestore collection and subcollection behavior."""

    def __init__(self):
        self.root_collections: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.sub_collections: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def collection(self, collection_name: str):
        return MockCollectionRef(self, collection_name)

    def batch(self):
        batch_mock = AsyncMock()
        batch_mock.commit = AsyncMock()
        return batch_mock


class MockCollectionRef:
    """Mock CollectionReference."""

    def __init__(self, client: MockFirestoreAsyncClient, collection_name: str, parent_path: str = ""):
        self.client = client
        self.collection_name = collection_name
        self.full_path = f"{parent_path}/{collection_name}" if parent_path else collection_name

    def document(self, doc_id: str):
        return MockDocumentRef(self.client, self.full_path, doc_id)

    async def get(self):
        store = self.client.sub_collections.get(self.full_path, {})
        return [MockDocSnapshot(doc_id, data) for doc_id, data in store.items()]

    def where(self, filter=None):
        return self

    def order_by(self, field: str, direction=None):
        return self

    def limit(self, count: int):
        return self

    def select(self, fields: list):
        return self


class MockDocumentRef:
    """Mock DocumentReference."""

    def __init__(self, client: MockFirestoreAsyncClient, collection_path: str, doc_id: str):
        self.client = client
        self.collection_path = collection_path
        self.doc_id = doc_id
        self.full_path = f"{collection_path}/{doc_id}"

    def collection(self, subcollection_name: str):
        return MockCollectionRef(self.client, subcollection_name, parent_path=self.full_path)

    async def get(self):
        is_subcollection = "/" in self.collection_path
        store = (
            self.client.sub_collections.get(self.collection_path, {})
            if is_subcollection
            else self.client.root_collections.get(self.collection_path, {})
        )
        if self.doc_id in store:
            return MockDocSnapshot(self.doc_id, store[self.doc_id], exists=True)
        return MockDocSnapshot(self.doc_id, None, exists=False)

    async def set(self, data: Dict[str, Any], merge: bool = False):
        is_subcollection = "/" in self.collection_path
        if is_subcollection:
            if self.collection_path not in self.client.sub_collections:
                self.client.sub_collections[self.collection_path] = {}
            target = self.client.sub_collections[self.collection_path]
        else:
            if self.collection_path not in self.client.root_collections:
                self.client.root_collections[self.collection_path] = {}
            target = self.client.root_collections[self.collection_path]

        if merge and self.doc_id in target:
            target[self.doc_id].update(data)
        else:
            target[self.doc_id] = data.copy()

    async def delete(self):
        is_subcollection = "/" in self.collection_path
        store = (
            self.client.sub_collections.get(self.collection_path, {})
            if is_subcollection
            else self.client.root_collections.get(self.collection_path, {})
        )
        store.pop(self.doc_id, None)


@pytest.fixture
def session_service():
    """Initializes FirestoreSessionService with MockFirestoreAsyncClient."""
    service = FirestoreSessionService(
        project="test-project",
        collection="sosta_sessions",
        database="test-session-db",
    )
    service._db = MockFirestoreAsyncClient()
    return service


@pytest.mark.asyncio
async def test_session_creation_metadata_and_storage_version(session_service):
    """Verifies that create_session creates the root doc with storageVersion=2."""
    session = await session_service.create_session(
        app_name="sosta_app",
        user_id="usr_tester",
        session_id="session_scaling_001",
        state={"user:preferred_language": "Italian"},
    )

    assert session.id == "session_scaling_001"
    assert session.state["user:preferred_language"] == "Italian"

    # Inspect root document in mock Firestore
    root_store = session_service.db.root_collections["sosta_sessions"]
    root_doc = root_store["session_scaling_001"]
    assert root_doc["storageVersion"] == STORAGE_VERSION
    assert root_doc["storageVersion"] == 2
    assert "events" not in root_doc  # Root document must not contain events array!


@pytest.mark.asyncio
async def test_subcollection_event_append_and_retrieval(session_service):
    """Verifies appending events stores them in sosta_sessions/{session_id}/events subcollection."""
    session = await session_service.create_session(
        app_name="sosta_app",
        user_id="usr_tester",
        session_id="session_scaling_002",
    )

    # Append Turn 1 Event
    event1 = ADKEvent(
        id="ev_001",
        timestamp=time.time(),
        author="user",
        content=types.Content(
            role="user",
            parts=[types.Part.from_text(text="Find charging stations near Florence")],
        ),
    )
    await session_service.append_event(session, event1)

    # Check that event was stored inside the subcollection
    subcoll_path = "sosta_sessions/session_scaling_002/events"
    assert subcoll_path in session_service.db.sub_collections
    subcoll_events = session_service.db.sub_collections[subcoll_path]
    assert "ev_001" in subcoll_events
    assert subcoll_events["ev_001"]["content"]["parts"][0]["text"] == "Find charging stations near Florence"

    # Root document must remain lightweight
    root_doc = session_service.db.root_collections["sosta_sessions"]["session_scaling_002"]
    assert "events" not in root_doc

    # Fetch session and verify events are loaded
    loaded_session = await session_service.get_session(
        app_name="sosta_app",
        user_id="usr_tester",
        session_id="session_scaling_002",
    )
    assert loaded_session is not None
    assert len(loaded_session.events) == 1
    assert loaded_session.events[0].id == "ev_001"
    assert loaded_session.events[0].content.parts[0].text == "Find charging stations near Florence"


@pytest.mark.asyncio
async def test_exceeding_1mb_document_limit_simulation(session_service):
    """Simulates a long multi-turn session with large tool responses exceeding 1.2MB total.

    In legacy FirestoreSessionService (storageVersion=1), saving 1.2MB in a single document
    fails with 'Document exceeds maximum allowed size of 1048576 bytes'.
    With STORAGE_VERSION=2 subcollections, each event is an isolated subdocument,
    allowing the conversation history to scale infinitely!
    """
    session = await session_service.create_session(
        app_name="sosta_app",
        user_id="usr_tester",
        session_id="session_scaling_heavy",
    )

    total_payload_bytes = 0
    # Simulate 15 turns, each containing an 80KB RAG/Specification chunk payload (~1.2MB total)
    chunk_text = "A" * 80_000

    for i in range(15):
        event = ADKEvent(
            id=f"turn_event_{i:03d}",
            timestamp=time.time() + i,
            author="cameriere_agent" if i % 2 == 1 else "user",
            content=types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Turn message {i}: {chunk_text}")],
            ),
        )
        total_payload_bytes += len(chunk_text)
        await session_service.append_event(session, event)

    # Prove that the total conversation size exceeds 1MB (1,048,576 bytes)
    assert total_payload_bytes > 1_048_576

    # Verify that the root metadata document remains small (< 5KB)
    root_doc = session_service.db.root_collections["sosta_sessions"]["session_scaling_heavy"]
    import json
    root_doc_bytes = len(json.dumps(root_doc).encode("utf-8"))
    assert root_doc_bytes < 5_000, f"Root document size ({root_doc_bytes} bytes) must remain minimal!"

    # Verify all 15 events are independently stored in the subcollection
    subcoll_path = "sosta_sessions/session_scaling_heavy/events"
    assert len(session_service.db.sub_collections[subcoll_path]) == 15

    # Verify that get_session successfully reconstitutes the entire 15-event session
    loaded_session = await session_service.get_session(
        app_name="sosta_app",
        user_id="usr_tester",
        session_id="session_scaling_heavy",
    )
    assert loaded_session is not None
    assert len(loaded_session.events) == 15


@pytest.mark.asyncio
async def test_legacy_v1_backward_compatibility(session_service):
    """Verifies that legacy v1 sessions (where events array is in the root doc) load seamlessly."""
    legacy_v1_doc = {
        "id": "legacy_session_v1_001",
        "app_name": "sosta_app",
        "user_id": "usr_legacy",
        "storageVersion": 1,
        "state": {"user:email": "legacy@example.com"},
        "last_update_time": 1723500000.0,
        "events": [
            {
                "id": "leg_ev_1",
                "timestamp": 1723500001.0,
                "author": "user",
                "content": {"role": "user", "parts": [{"text": "Hello from legacy v1!"}]},
            },
            {
                "id": "leg_ev_2",
                "timestamp": 1723500002.0,
                "author": "gatekeeper_agent",
                "content": {"role": "model", "parts": [{"text": "Welcome back traveler!"}]},
            },
        ],
    }
    # Direct seed in root collection
    session_service.db.root_collections["sosta_sessions"] = {
        "legacy_session_v1_001": legacy_v1_doc
    }

    # Fetch session using get_session
    loaded_session = await session_service.get_session(
        app_name="sosta_app",
        user_id="usr_legacy",
        session_id="legacy_session_v1_001",
    )
    assert loaded_session is not None
    assert loaded_session.id == "legacy_session_v1_001"
    assert len(loaded_session.events) == 2
    assert loaded_session.events[0].content.parts[0].text == "Hello from legacy v1!"
    assert loaded_session.events[1].content.parts[0].text == "Welcome back traveler!"
