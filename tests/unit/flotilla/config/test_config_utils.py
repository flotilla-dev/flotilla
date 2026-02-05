from flotilla.config.config_utils import ConfigUtils
import pytest

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

# ---------------------------------------------------------------------------
# resolve_flattened_config
# ---------------------------------------------------------------------------

def test_resolve_flattened_config_returns_none_if_base_missing():
    config = {
        "llm": {
            "openai": {
                "model": "gpt-4",
            }
        }
    }

    result = ConfigUtils.resolve_flattened_config(
        config=config,
        base_path="llm.anthropic",
    )

    assert result is None


def test_resolve_flattened_config_returns_none_if_base_not_mapping():
    config = {
        "llm": {
            "openai": "gpt-4",
        }
    }

    result = ConfigUtils.resolve_flattened_config(
        config=config,
        base_path="llm.openai",
    )

    assert result is None


def test_resolve_flattened_config_ignores_missing_override():
    config = {
        "llm": {
            "openai": {
                "model": "gpt-4",
                "temperature": 0.7,
            }
        }
    }

    result = ConfigUtils.resolve_flattened_config(
        config=config,
        base_path="llm.openai",
        override_path="agents.missing.llm",
    )

    assert result == {
        "model": "gpt-4",
        "temperature": 0.7,
    }


def test_resolve_flattened_config_ignores_non_mapping_override():
    config = {
        "llm": {
            "openai": {
                "model": "gpt-4",
                "temperature": 0.7,
            }
        },
        "agents": {
            "agent_a": {
                "llm": "override",
            }
        }
    }

    result = ConfigUtils.resolve_flattened_config(
        config=config,
        base_path="llm.openai",
        override_path="agents.agent_a.llm",
    )

    assert result == {
        "model": "gpt-4",
        "temperature": 0.7,
    }


def test_resolve_flattened_config_deep_merges_override():
    config = {
        "llm": {
            "openai": {
                "model": "gpt-4",
                "params": {
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            }
        },
        "agents": {
            "agent_a": {
                "llm": {
                    "params": {
                        "temperature": 0.3,
                    }
                }
            }
        }
    }

    result = ConfigUtils.resolve_flattened_config(
        config=config,
        base_path="llm.openai",
        override_path="agents.agent_a.llm",
    )

    assert result == {
        "model": "gpt-4",
        "params": {
            "temperature": 0.3,
            "max_tokens": 2048,
        },
    }


    # ---------------------------------------------------------------------------
# resolve_config_refs ($config)
# ---------------------------------------------------------------------------

def test_resolve_config_refs_basic():
    config = {
        "llm": {
            "base": {
                "model": "gpt-4",
                "temperature": 0.0,
            }
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
            }
        }
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert resolved["agent"]["llm"] == {
        "model": "gpt-4",
        "temperature": 0.0,
    }


def test_resolve_config_refs_with_overrides():
    config = {
        "llm": {
            "base": {
                "model": "gpt-4",
                "temperature": 0.0,
            }
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
                "overrides": {
                    "temperature": 0.7,
                },
            }
        }
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert resolved["agent"]["llm"] == {
        "model": "gpt-4",
        "temperature": 0.7,
    }


def test_resolve_config_refs_nested_resolution():
    config = {
        "llm": {
            "base": {
                "model": "gpt-4",
            }
        },
        "tools": {
            "search": {
                "llm": {
                    "$config": "llm.base",
                }
            }
        },
        "agent": {
            "tools": [
                {
                    "$config": "tools.search",
                }
            ]
        }
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert resolved["agent"]["tools"] == [
        {
            "llm": {
                "model": "gpt-4",
            }
        }
    ]


def test_resolve_config_refs_recursive_overrides():
    config = {
        "llm": {
            "base": {
                "model": "gpt-4",
                "params": {
                    "temperature": 0.0,
                    "max_tokens": 2048,
                },
            }
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
                "overrides": {
                    "params": {
                        "temperature": 0.5,
                    }
                },
            }
        }
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert resolved["agent"]["llm"] == {
        "model": "gpt-4",
        "params": {
            "temperature": 0.5,
            "max_tokens": 2048,
        },
    }


def test_resolve_config_refs_raises_if_path_missing():
    config = {
        "agent": {
            "llm": {
                "$config": "llm.missing",
            }
        }
    }

    try:
        ConfigUtils.resolve_config_refs(config, root=config)
    except ValueError as e:
        assert "llm.missing" in str(e)
    else:
        assert False, "Expected ValueError for missing $config path"


def test_resolve_config_refs_raises_if_target_not_mapping():
    config = {
        "llm": {
            "base": "gpt-4",
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
            }
        }
    }

    try:
        ConfigUtils.resolve_config_refs(config, root=config)
    except ValueError as e:
        assert "$config 'llm.base' must resolve to a config object" in str(e)
    else:
        assert False, "Expected ValueError for non-mapping $config target"


def test_resolve_config_refs_does_not_mutate_original():
    config = {
        "llm": {
            "base": {
                "model": "gpt-4",
            }
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
            }
        }
    }

    original = {
        "llm": {
            "base": {
                "model": "gpt-4",
            }
        },
        "agent": {
            "llm": {
                "$config": "llm.base",
            }
        }
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert config == original
    assert resolved["agent"]["llm"] == {"model": "gpt-4"}


def test_config_cycle_direct():
    config = {
        "a": {
            "$config": "a"
        }
    }

    with pytest.raises(ValueError) as exc:
        ConfigUtils.resolve_config_refs(config, root=config)

    assert "cycle detected" in str(exc.value)


def test_config_cycle_indirect():
    config = {
        "a": {"$config": "b"},
        "b": {"$config": "c"},
        "c": {"$config": "a"},
    }

    with pytest.raises(ValueError) as exc:
        ConfigUtils.resolve_config_refs(config, root=config)

    msg = str(exc.value)

    assert "cycle detected" in msg
    assert all(x in msg for x in ("a", "b", "c"))



def test_config_reuse_without_cycle():
    config = {
        "base": {"x": 1},
        "a": {"$config": "base"},
        "b": {"$config": "base"},
    }

    resolved = ConfigUtils.resolve_config_refs(config, root=config)

    assert resolved["a"] == {"x": 1}
    assert resolved["b"] == {"x": 1}
