from typing import Any

from pydantic import BaseModel
from flotilla.thread.thread_entries import ThreadEntry
from flotilla.thread.thread_service import ThreadService
from flotilla_fastapi.handler import HTTPHandler
from flotilla_fastapi.routes import routes


class CreateThreadResponse(BaseModel):
    thread_id: str


class LoadThreadResponse(BaseModel):
    thread_id: str
    entries: list[dict[str, Any]]


class ThreadHandler(HTTPHandler):
    def __init__(self, thread_service: ThreadService):
        self._thread_service = thread_service

    @routes.post("/threads", status_code=201)
    async def create_thread(self) -> CreateThreadResponse:
        thread_id = await self._thread_service.create_thread()
        return CreateThreadResponse(thread_id=thread_id)

    @routes.get("/threads/{thread_id}")
    async def load_thread(self, thread_id: str) -> LoadThreadResponse:
        entries = await self._thread_service.load(thread_id=thread_id)
        return LoadThreadResponse(
            thread_id=thread_id,
            entries=[self._serialize_entry(entry) for entry in entries],
        )

    def _serialize_entry(self, entry: ThreadEntry) -> dict[str, Any]:
        return entry.model_dump(mode="json", exclude_none=True)
