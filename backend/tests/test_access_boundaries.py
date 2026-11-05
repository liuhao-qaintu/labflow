"""权限、数据归属和公开响应；不连接业务数据库，不调用模型或写真实预约。"""
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import TypedDict
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from app.access import PublicImageFiles, public_chat_event, user_checkpoint_config
from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.router import ai, upload, user
from app.services import agent_service, reservation_service
from app.common.exceptions import BusinessException, business_exception_handler


class RequestAccessTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(ai.router)
        self.app.include_router(upload.router)
        self.app.include_router(user.router)
        self.app.add_exception_handler(BusinessException, business_exception_handler)
        self.app.dependency_overrides[get_db] = lambda: None
        self.client = TestClient(self.app)

    def identity(self, role='student', uid=1):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role, id=uid, status=1)

    def test_unauthenticated_upload_and_developer_api_are_denied(self):
        self.assertEqual(self.client.post('/files/upload', files={'file': ('x.png', b'not-an-image')}).status_code, 401)
        self.assertEqual(self.client.post('/ai/kb/search', json={'query': 'rules'}).status_code, 401)

    def test_student_cannot_call_user_management_or_rebuild_directly(self):
        self.identity()
        self.assertEqual(self.client.get('/user/list').status_code, 403)
        with patch.object(ai.kb_service, 'build_index') as build:
            self.assertEqual(self.client.post('/ai/kb/rebuild').status_code, 403)
        build.assert_not_called()

    def test_business_admin_is_not_automatically_a_developer(self):
        self.identity('admin')
        with patch.object(settings, 'DEVELOPER_USER_IDS', []), patch.object(ai.kb_service, 'search') as search:
            self.assertEqual(self.client.post('/ai/kb/search', json={'query': 'rules'}).status_code, 403)
        search.assert_not_called()

    def test_configured_maintainer_can_rebuild(self):
        self.identity('admin', 7)
        with patch.object(settings, 'DEVELOPER_USER_IDS', [7]), patch.object(ai.kb_service, 'build_index', return_value=4) as build, patch.object(ai.kb_service, 'reload'):
            self.assertEqual(self.client.post('/ai/kb/rebuild').status_code, 200)
        build.assert_called_once()

    def test_office_document_cannot_be_uploaded_as_public_media(self):
        self.identity()
        result = self.client.post('/files/upload', files={'file': ('private.pdf', b'%PDF private')})
        self.assertNotEqual(result.json()['code'], 200)

    def test_image_suffix_does_not_allow_html_upload(self):
        self.identity()
        result = self.client.post('/files/upload', files={'file': ('fake.png', b'<html>private</html>')})
        self.assertNotEqual(result.json()['code'], 200)

    def test_actual_stream_endpoint_drops_tool_output_and_keeps_answer(self):
        self.identity()
        class FakeSession:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def get(self, *_): return SimpleNamespace(id=1, role='student', status=1)
        async def stream(*args, **kwargs):
            yield {'type': 'tool_end', 'name': 'internal_search', 'preview': 'PRIVATE_SQL_TRACE'}
            yield {'type': 'token', 'content': '公开回答'}
            yield {'type': 'done'}
        with patch.object(ai, 'SessionLocal', return_value=FakeSession()), patch.object(ai.agent_service, 'stream_agent', stream):
            response = self.client.post('/ai/chat/stream', json={'messages': [{'role': 'user', 'content': '开放时间？'}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn('公开回答', response.text)
        self.assertNotIn('PRIVATE_SQL_TRACE', response.text)
        self.assertNotIn('internal_search', response.text)

    def test_foreign_reservation_cannot_be_cancelled(self):
        item = SimpleNamespace(user_id=2, status=0)
        db = SimpleNamespace(query=lambda _: SimpleNamespace(filter=lambda _: SimpleNamespace(first=lambda: item)), commit=lambda: self.fail('must not commit'))
        with self.assertRaises(BusinessException) as raised:
            reservation_service.cancel_reservation(db, SimpleNamespace(id=1), 20)
        self.assertEqual(raised.exception.code, 403)


class PublicOutputTests(unittest.TestCase):
    def test_raw_tool_preview_and_unknown_debug_event_never_reach_client(self):
        event = {'type': 'tool_end', 'name': 'search_kb', 'preview': 'PRIVATE_SQL_TRACE'}
        self.assertNotIn('PRIVATE_SQL_TRACE', str(public_chat_event(event)))
        self.assertNotIn('name', public_chat_event(event))
        self.assertIsNone(public_chat_event({'type': 'debug', 'trace': 'private'}))

    def test_confirmation_preserves_business_fields_only(self):
        event = {'type': 'interrupt', 'thread_id': 'public-id', 'action': 'internal_tool',
                 'payload': {'question': 'internal step', 'args': {'lab_id': 2, 'date': '2026-11-05', 'user_id': 999, 'sql': 'private'}}}
        projected = public_chat_event(event)
        self.assertEqual(projected['payload']['args'], {'lab_id': 2, 'date': '2026-11-05'})
        self.assertNotIn('internal_tool', str(projected))

    def test_error_projection_does_not_expose_backend_exception(self):
        self.assertNotIn('PRIVATE_DATABASE_URL', str(public_chat_event({'type': 'error', 'message': 'PRIVATE_DATABASE_URL'})))

    def test_static_upload_mount_does_not_serve_existing_private_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'notes.pdf').write_bytes(b'%PDF confidential')
            Path(directory, 'avatar.png').write_bytes(b'public fixture')
            app = FastAPI(); app.mount('/uploads', PublicImageFiles(directory=directory))
            with TestClient(app) as client:
                self.assertEqual(client.get('/uploads/notes.pdf').status_code, 404)
                self.assertEqual(client.get('/uploads/avatar.png').status_code, 200)


class CheckpointScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_client_thread_id_cannot_read_another_users_checkpoint(self):
        class State(TypedDict):
            secret: str
        graph = StateGraph(State)
        graph.add_node('store', lambda state: state)
        graph.add_edge(START, 'store'); graph.add_edge('store', END)
        graph = graph.compile(checkpointer=MemorySaver())
        await graph.ainvoke({'secret': 'USER_A_PRIVATE'}, user_checkpoint_config('same-client-id', 1))
        a = await graph.aget_state(user_checkpoint_config('same-client-id', 1))
        b = await graph.aget_state(user_checkpoint_config('same-client-id', 2))
        self.assertEqual(a.values['secret'], 'USER_A_PRIVATE')
        self.assertEqual(b.values, {})

    async def test_missing_foreign_or_already_consumed_confirmation_does_not_run_tools(self):
        graph = SimpleNamespace(aget_state=AsyncMock(return_value=SimpleNamespace(tasks=())), ainvoke=AsyncMock())
        with patch.object(agent_service, 'build_agent', return_value=graph):
            with self.assertRaises(BusinessException) as raised:
                await agent_service.resume_agent(None, SimpleNamespace(id=2), 'another-users-thread', True)
        self.assertEqual(raised.exception.code, 409)
        graph.ainvoke.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
