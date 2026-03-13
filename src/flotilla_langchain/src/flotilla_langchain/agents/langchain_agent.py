from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional, Any
import asyncio
import json
import inspect
from functools import update_wrapper

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
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
from flotilla.thread.thread_entries import ThreadEntry, UserInput, ResumeEntry

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
        subgraphs: Optional[bool] = True,
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
        fn = tool.execution_callable  # bound method
        instance = fn.__self__
        func = fn.__func__  # underlying function

        def tool_func(*args, **kwargs):
            return func(instance, *args, **kwargs)

        # preserve metadata
        update_wrapper(tool_func, func)

        # preserve the original signature (minus self)
        sig = inspect.signature(func)
        params = list(sig.parameters.values())[1:]  # drop "self"
        tool_func.__signature__ = sig.replace(parameters=params)

        return StructuredTool.from_function(
            func=tool_func,
            name=func.__name__,
            description=tool.llm_description,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute(
        self,
        thread_context: ThreadContext,
        phase_context: PhaseContext,
        input_parts: Optional[List[ContentPart]] = None,
    ) -> AsyncIterator[AgentEvent]:

        if not thread_context.entries:
            raise RuntimeError("ThreadContext must contain at least one entry.")

        triggering_entry = thread_context.entries[-1]
        entry_id = triggering_entry.entry_id

        if not entry_id:
            raise RuntimeError("Triggering entry must have a non-null entry_id.")

        yield AgentEvent.message_start(entry_id=entry_id, agent_id=self.agent_name)

        chunk_buffer: List[str] = []
        stream_metadata: Dict[str, Any] = {}
        last_ai_message: Optional[AIMessage] = None

        command = self._resume_command(triggering_entry)
        graph_config = self._graph_config(phase_context)

        try:
            async for event in self._graph.astream(
                self._graph_input(thread=thread_context, config=phase_context),
                command=command,
                stream_mode=["messages", "updates"],
                subgraphs=self._subgraphs,
                config=graph_config,
            ):
                mode = event[1]
                chunk = event[2]

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

            logger.info(f"StateSnapshot type {type(final_state)}")

            messages = final_state.values.get("messages", [])
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

        messages = []

        for entry in thread.entries:
            text = " ".join(p.text for p in entry.content if isinstance(p, TextPart))

            if isinstance(entry, UserInput) or isinstance(entry, ResumeEntry):
                messages.append(HumanMessage(content=text))
            else:
                messages.append(AIMessage(content=text))

        return {
            "messages": messages,
            "configurable": {
                "thread_id": config.thread_id,
            },
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
