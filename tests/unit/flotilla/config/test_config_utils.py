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

def test_deep_merge_override_dict_with_scalar():
    base = {"a": {"x": 1}}
    override = {"a": 5}

    result = ConfigUtils.deep_merge(base, override)

    assert result["a"] == 5


def test_deep_merge_override_scalar_with_dict():
    base = {"a": 5}
    override = {"a": {"x": 1}}

    result = ConfigUtils.deep_merge(base, override)

    assert result["a"] == {"x": 1}


def test_deep_merge_list_is_replaced():
    base = {"items": [1, 2, 3]}
    override = {"items": [4]}

    result = ConfigUtils.deep_merge(base, override)

    assert result["items"] == [4]


def test_deep_merge_nested_mixed_keys():
    base = {
        "a": {
            "x": 1,
            "y": 2,
        }
    }
    override = {
        "a": {
            "y": 99,
            "z": 3,
        }
    }

    result = ConfigUtils.deep_merge(base, override)

    assert result == {
        "a": {
            "x": 1,
            "y": 99,
            "z": 3,
        }
    }


def test_deep_merge_none_override_wins():
    base = {"a": 1}
    override = {"a": None}

    result = ConfigUtils.deep_merge(base, override)

    assert result["a"] is None


def test_deep_merge_does_not_mutate_base():
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}

    result = ConfigUtils.deep_merge(base, override)

    assert base == {"a": {"x": 1}}
    assert result == {"a": {"x": 1, "y": 2}}

def test_walk_and_replace_simple_value():
    data = {"a": 1}

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: v * 2 if isinstance(v, int) else v,
    )

    assert result == {"a": 2}


def test_walk_and_replace_nested_dict():
    data = {"a": {"b": 2}}

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: v + 1 if isinstance(v, int) else v,
    )

    assert result == {"a": {"b": 3}}

def test_walk_and_replace_list_values():
    data = {"items": [1, 2, 3]}

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: v * 10 if isinstance(v, int) else v,
    )

    assert result == {"items": [10, 20, 30]}

def test_walk_and_replace_mixed_nesting():
    data = {
        "a": [
            {"b": 1},
            {"c": 2},
        ]
    }

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: v + 5 if isinstance(v, int) else v,
    )

    assert result == {
        "a": [
            {"b": 6},
            {"c": 7},
        ]
    }

def test_walk_and_replace_allows_none_replacement():
    data = {"a": "secret"}

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: None if v == "secret" else v,
    )

    assert result == {"a": None}

def test_walk_and_replace_does_not_mutate_input():
    data = {"a": {"b": 1}}

    result = ConfigUtils.walk_and_replace(
        data,
        lambda v: v * 2 if isinstance(v, int) else v,
    )

    assert data == {"a": {"b": 1}}
    assert result == {"a": {"b": 2}}

