from flotilla.config.config_utils import ConfigUtils


def test_deep_merge_simple():
    a = {"x": 1}
    b = {"y": 2}

    result = ConfigUtils.deep_merge(a, b)

    assert result == {"x": 1, "y": 2}


def test_deep_merge_nested_override():
    a = {"core": {"enabled": False}}
    b = {"core": {"enabled": True}}

    result = ConfigUtils.deep_merge(a, b)

    assert result["core"]["enabled"] is True
