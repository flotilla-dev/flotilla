import asyncio

import pytest

from flotilla.config.sources.python_configuration_source import PythonConfigurationSource


def test_python_configuration_source_loads_function():
    def configure():
        return {"a": 1}

    source = PythonConfigurationSource(configure)

    assert asyncio.run(source.load()) == {"a": 1}


def test_python_configuration_source_merges_functions_in_order():
    def base():
        return {"component": {"model": "base", "temperature": 0.1}}

    def override():
        return {"component": {"model": "override"}}

    source = PythonConfigurationSource([base, override])

    assert asyncio.run(source.load()) == {
        "component": {
            "model": "override",
            "temperature": 0.1,
        }
    }


def test_python_configuration_source_supports_async_functions():
    async def configure():
        return {"a": 1}

    source = PythonConfigurationSource(configure)

    assert asyncio.run(source.load()) == {"a": 1}


def test_python_configuration_source_from_object_uses_explicit_methods():
    class Config:
        def runtime(self):
            return {"runtime": {"$provider": "runtime.default"}}

        def agents(self):
            return {"agent": {"$provider": "agents.default"}}

    source = PythonConfigurationSource.from_object(Config(), methods=["runtime", "agents"])

    assert asyncio.run(source.load()) == {
        "runtime": {"$provider": "runtime.default"},
        "agent": {"$provider": "agents.default"},
    }


def test_python_configuration_source_rejects_non_dict_return():
    def configure():
        return "not a dict"

    source = PythonConfigurationSource(configure)

    with pytest.raises(TypeError):
        asyncio.run(source.load())
