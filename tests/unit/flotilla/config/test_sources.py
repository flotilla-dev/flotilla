import pytest

from flotilla.config.sources import DictConfigurationSource


def test_dict_configuration_source_loads_data():
    source = DictConfigurationSource(
        {
            "core": {"enabled": True}
        }
    )

    config = source.load()

    assert config["core"]["enabled"] is True


def test_dict_configuration_source_empty():
    source = DictConfigurationSource({})

    config = source.load()

    assert config == {}

def test_multiple_sources_merge_later_overrides():
    s1 = DictConfigurationSource({"core": {"enabled": False}})
    s2 = DictConfigurationSource({"core": {"enabled": True}})

    merged = {}
    merged.update(s1.load())
    merged.update(s2.load())

    assert merged["core"]["enabled"] is True
