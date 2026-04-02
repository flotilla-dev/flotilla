import pytest
import inspect

from flotilla.tools.decorated_flotilla_tool import DecoratedFlotillaTool
from flotilla.tools.tool_decorators import tool_call


class DummyService:
    def get(self, x):
        return x * 2


class SyncTool(DecoratedFlotillaTool):

    def __init__(self):
        self.service = DummyService()

    @property
    def id(self):
        return "sync_tool"

    @property
    def name(self):
        return "Sync Tool"

    @property
    def llm_description(self):
        return "A simple sync tool."

    @tool_call
    def run(self, value: int):
        return self.service.get(value)


def test_sync_execution_callable_returns_bound_method():
    tool = SyncTool()

    method = tool.execution_callable
    assert callable(method)

    result = method(3)
    assert result == 6


class AsyncTool(DecoratedFlotillaTool):

    @property
    def id(self):
        return "async_tool"

    @property
    def name(self):
        return "Async Tool"

    @property
    def llm_description(self):
        return "A simple async tool."

    @tool_call
    async def run(self, value: int):
        return value + 5


@pytest.mark.asyncio
async def test_async_execution_callable():
    tool = AsyncTool()
    method = tool.execution_callable

    assert inspect.iscoroutinefunction(method)

    result = await method(7)
    assert result == 12


class GeneratorTool(DecoratedFlotillaTool):

    @property
    def id(self):
        return "gen_tool"

    @property
    def name(self):
        return "Generator Tool"

    @property
    def llm_description(self):
        return "Streams numbers."

    @tool_call
    def run(self, count: int):
        for i in range(count):
            yield i


def test_sync_generator_streaming():
    tool = GeneratorTool()
    method = tool.execution_callable

    result = method(3)

    assert list(result) == [0, 1, 2]


class AsyncGeneratorTool(DecoratedFlotillaTool):

    @property
    def id(self):
        return "async_gen_tool"

    @property
    def name(self):
        return "Async Generator Tool"

    @property
    def llm_description(self):
        return "Streams numbers async."

    @tool_call
    async def run(self, count: int):
        for i in range(count):
            yield i


@pytest.mark.asyncio
async def test_async_generator_streaming():
    tool = AsyncGeneratorTool()
    method = tool.execution_callable

    results = []
    async for item in method(3):
        results.append(item)

    assert results == [0, 1, 2]


def test_missing_decorated_method_raises():

    with pytest.raises(TypeError):

        class BadTool(DecoratedFlotillaTool):

            @property
            def id(self):
                return "bad"

            @property
            def name(self):
                return "Bad"

            @property
            def llm_description(self):
                return "No tool method defined."


def test_multiple_decorated_methods_raises():

    with pytest.raises(TypeError):

        class BadTool(DecoratedFlotillaTool):

            @property
            def id(self):
                return "bad"

            @property
            def name(self):
                return "Bad"

            @property
            def llm_description(self):
                return "Too many tool methods."

            @tool_call
            def run1(self):
                pass

            @tool_call
            def run2(self):
                pass


def test_inherited_tool_method_is_detected():
    class BaseTool(DecoratedFlotillaTool):

        @property
        def id(self):
            return "base"

        @property
        def name(self):
            return "Base"

        @property
        def llm_description(self):
            return "Base tool."

        @tool_call
        def run(self):
            return 1

    class ChildTool(BaseTool):
        pass

    tool = ChildTool()
    assert tool.execution_callable() == 1
