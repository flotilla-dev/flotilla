from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional, Any
import asyncio
import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Checkpointer
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool

from flotilla.agents.flotilla_agent import FlotillaAgent
from flotilla.agents.agent_event import AgentEvent
from flotilla.runtime.content_part import ContentPart, TextPart, JsonPart
from flotilla.runtime.phase_context import PhaseContext
from flotilla.thread.thread_context import ThreadContext
from flotilla.thread.thread_entries import ThreadEntry, ResumeEntry
from flotilla.tools.flotilla_tool import FlotillaTool
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


class LangChainAgent(FlotillaAgent):
    """
    LangChain-backed FlotillaAgent.

    - Streams tokens via message_chunk
    - Retrieves authoritative final graph state
    - Maps final AIMessage/state → ContentPart[]
    - Extracts optional execution metadata
    """

    def __init__(
        self,
        *,
        agent_name: str,
        llm: BaseChatModel,
        system_prompt: Optional[str] = None,
        tools: Optional[List[FlotillaTool]] = None,
        model_kwargs: Optional[Dict] = None,
        checkpointer: Optional[Checkpointer] = None,
        subgraphs: bool = True,
    ):
        self._llm = llm
        self._system_prompt = system_prompt
        self._tools = tools or []
        self._model_kwargs = model_kwargs or {}
        self._checkpointer = checkpointer
        self._subgraphs = subgraphs

        self._graph: CompiledStateGraph = self._build_graph()

        super().__init__(agent_name=agent_name)

    # ------------------------------------------------------------------
    # Graph Construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> CompiledStateGraph:
        structured_tools = [self._wrap_tool(t) for t in self._tools]

        return create_agent(
            model=self._llm,
            tools=structured_tools,
            system_prompt=self._system_prompt,
            checkpointer=self._checkpointer,
            **self._model_kwargs,
        )

    @staticmethod
    def _wrap_tool(tool: FlotillaTool) -> StructuredTool:
        return StructuredTool.from_function(
            func=tool.execution_callable,
            name=tool.name,
            description=tool.llm_description,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute(
        self,
        thread: ThreadContext,
        config: PhaseContext,
        input_parts: Optional[List[ContentPart]] = None,
    ) -> AsyncIterator[AgentEvent]:

        if not thread.entries:
            raise RuntimeError("ThreadContext must contain at least one entry.")

        triggering_entry = thread.entries[-1]
        entry_id = triggering_entry.entry_id

        if not entry_id:
            raise RuntimeError("Triggering entry must have a non-null entry_id.")

        yield AgentEvent.message_start(entry_id=entry_id, agent_id=self.agent_name)

        chunk_buffer: List[str] = []
        stream_metadata: Dict[str, Any] = {}
        last_ai_message: Optional[AIMessage] = None

        command = self._resume_command(triggering_entry)
        graph_config = self._graph_config(config)

        try:
            async for mode, chunk in self._graph.astream(
                self._graph_input(thread=thread, config=config),
                command=command,
                stream_mode=["messages", "updates"],
                subgraphs=self._subgraphs,
                config=graph_config,
            ):

                # -------------------------------------------------
                # STREAMING TOKENS
                # -------------------------------------------------
                if mode == "messages":
                    message, metadata = chunk

                    # capture metadata (last write wins or merge)
                    if isinstance(metadata, dict):
                        stream_metadata.update(metadata)

                    if isinstance(message, AIMessageChunk):
                        if message.content:
                            chunk_buffer.append(message.content)

                            yield AgentEvent.message_chunk(
                                entry_id=entry_id,
                                agent_id=self.agent_name,
                                text=message.content,
                            )

                # -------------------------------------------------
                # INTERRUPT / SUSPEND
                # -------------------------------------------------
                elif mode == "updates":
                    interrupt_payload = chunk.get("__interrupt__")
                    if interrupt_payload is not None:
                        reason = json.dumps(interrupt_payload, default=str)

                        yield AgentEvent.suspend(
                            entry_id=entry_id,
                            agent_id=self.agent_name,
                            content=[TextPart(text=reason)],
                        )
                        return

            # -------------------------------------------------
            # AUTHORITATIVE FINAL STATE
            # -------------------------------------------------

            final_state = await self._graph.aget_state(config=graph_config)

            messages = final_state.get("messages", [])
            if isinstance(messages, list):
                for m in reversed(messages):
                    if isinstance(m, AIMessage):
                        last_ai_message = m
                        break

            if last_ai_message is None:
                yield AgentEvent.error(
                    entry_id=entry_id,
                    agent_id=self.agent_name,
                    content=[TextPart(text="No AIMessage found in final state")],
                    metadata={"reason": "missing_ai_message"},
                )
                return

            final_text = "".join(chunk_buffer)

            parts = self._map_final_output_to_content_parts(
                final_text=final_text,
                final_message=last_ai_message,
                final_state=final_state,
                stream_metadata=stream_metadata,
            )

            execution_metadata = self._extract_execution_metadata(
                final_message=last_ai_message,
                final_state=final_state,
                stream_metadata=stream_metadata,
            )

            yield AgentEvent.message_final(
                entry_id=entry_id,
                agent_id=self.agent_name,
                content=parts,
                metadata=execution_metadata,
            )

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.error(
                f"Error while executing LangChainAgent {self.agent_name}",
                exc_info=True,
            )

            yield AgentEvent.error(
                entry_id=entry_id,
                agent_id=self.agent_name,
                content=[TextPart(text=str(e))],
            )

    # ------------------------------------------------------------------
    # Extension Hooks
    # ------------------------------------------------------------------

    def _map_final_output_to_content_parts(
        self,
        *,
        final_text: str,
        final_message: Optional[AIMessage],
        final_state: Optional[Dict[str, Any]],
        stream_metadata: Dict[str, Any],
    ) -> List[ContentPart]:
        """
        Map authoritative final output → ContentPart[].

        Override to support:
        - JSON-first agents
        - File output agents
        - Multimodal agents
        - Custom response contracts
        """

        if final_message and isinstance(final_message.content, str):
            return [TextPart(text=final_message.content)]

        return [TextPart(text=final_text)]

    def _extract_execution_metadata(
        self,
        *,
        final_message: Optional[AIMessage],
        final_state: Optional[Dict[str, Any]],
        stream_metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Extract execution telemetry (token usage, timing, etc).

        Default: return stream_metadata if non-empty.
        """

        return stream_metadata or None

    # ------------------------------------------------------------------
    # Graph Helpers
    # ------------------------------------------------------------------

    def _graph_input(
        self,
        thread: ThreadContext,
        config: PhaseContext,
    ) -> Dict[str, Any]:
        """
        Override to customize graph input structure.
        """
        return {
            "configurable": {
                "thread_id": config.thread_id,
            }
        }

    def _graph_config(self, config: PhaseContext) -> Dict[str, Any]:
        return {
            "configurable": {
                "thread_id": config.thread_id,
            }
        }

    def _resume_command(self, entry: ThreadEntry) -> Optional[Command]:
        if not isinstance(entry, ResumeEntry):
            return None

        payload = self._map_resume_content_to_payload(entry.content)

        return Command(resume=payload)

    def _map_resume_content_to_payload(self, content: List[ContentPart]) -> Any:
        """
        Convert ResumeEntry content into a JSON-serializable
        payload suitable for LangGraph Command(resume=...).

        Default behavior:
        - Single JsonPart → return .data
        - Single TextPart → return .text
        - Otherwise → return list of serialized parts
        """

        if not content:
            return None

        if len(content) == 1:
            part = content[0]

            if isinstance(part, JsonPart):
                return part.data

            if isinstance(part, TextPart):
                return part.text

        # Fallback: structured representation
        return [p.model_dump() for p in content]
