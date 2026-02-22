from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional
import asyncio
import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Checkpointer

from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.core.agent_event import AgentEvent, AgentEventType
from flotilla.core.execution_config import ExecutionConfig
from flotilla.core.thread_context import ThreadContext
from flotilla.core.thread_entries import ResumeEntry
from flotilla.core.content_part import TextPart
from flotilla.tools.flotilla_tool import FlotillaTool


class LangChainAgent(FlotillaAgent):
    """
    LangChain-backed FlotillaAgent.

    - Graph compiled once at construction
    - message_id derived from triggering ThreadEntry
    - Supports LangGraph interrupts
    - Optional Checkpointer injection
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[FlotillaTool]] = None,
        model_kwargs: Optional[Dict] = None,
        *,
        checkpointer: Optional[Checkpointer] = None,
        subgraphs: bool = True,
    ):
        self._llm = llm
        self._tools = tools or []
        self._model_kwargs = model_kwargs or {}
        self._checkpointer = checkpointer
        self._subgraphs = subgraphs

        self._graph: CompiledStateGraph = self._build_graph()
        super().__init__()

    # ------------------------------------------------------------------
    # Extension Plane
    # ------------------------------------------------------------------

    def _build_graph(self) -> CompiledStateGraph:
        """
        Subclasses construct graph here.
        Must use injected llm, tools, and checkpointer.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute(
        self,
        thread: ThreadContext,
        config: ExecutionConfig,
    ) -> AsyncIterator[AgentEvent]:

        if not thread.entries:
            raise RuntimeError("ThreadContext must contain at least one entry.")

        triggering_entry = thread.entries[-1]
        message_id = triggering_entry.message_id

        yield AgentEvent(
            type=AgentEventType.MESSAGE_START,
            message_id=message_id,
        )

        chunk_buffer: List[str] = []
        emitted_chunk = False

        command = self._resume_command(triggering_entry)

        try:
            async for _meta, mode, chunk in self._graph.astream(
                self._graph_input(thread),
                command=command,
                stream_mode=["messages", "updates"],
                subgraphs=self._subgraphs,
                config={"configurable": {"thread_id": thread.thread_id}},
                recursion_limit=config.recursion_limit,
            ):
                # ------------------------------
                # Token streaming
                # ------------------------------
                if mode == "messages":
                    msg, _ = chunk
                    if isinstance(msg, AIMessageChunk) and msg.content:
                        text = msg.content
                        emitted_chunk = True
                        chunk_buffer.append(text)

                        yield AgentEvent(
                            type=AgentEventType.MESSAGE_CHUNK,
                            message_id=message_id,
                            content_text=text,
                        )

                # ------------------------------
                # Interrupt detection
                # ------------------------------
                elif mode == "updates":
                    if "__interrupt__" in chunk:
                        reason = json.dumps(chunk["__interrupt__"], default=str)
                        yield AgentEvent(
                            type=AgentEventType.SUSPEND,
                            reason=reason,
                        )
                        return

            # ------------------------------
            # Normal completion
            # ------------------------------
            final_text = "".join(chunk_buffer) if emitted_chunk else ""

            yield AgentEvent(
                type=AgentEventType.MESSAGE_FINAL,
                message_id=message_id,
                content=[TextPart(type="text", text=final_text)],
            )

        except asyncio.CancelledError:
            raise

        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.ERROR,
                message=str(e),
                recoverable=True,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _graph_input(self, thread: ThreadContext) -> Dict:
        return {
            "thread_id": thread.thread_id,
        }

    def _resume_command(self, entry) -> Optional[Command]:
        if isinstance(entry, ResumeEntry):
            return Command(
                action=getattr(entry, "action", None),
                resume=getattr(entry, "payload", None),
            )
        return None
