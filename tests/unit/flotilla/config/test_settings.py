from flotilla.config.settings import FlotillaSettings


def test_settings_from_empty_dict():
    settings = FlotillaSettings.from_dict({})

    assert settings is not None
    assert settings.model_dump(exclude_none=True) == {}


def test_settings_from_simple_dict():
    data = {
        "tools": {
            "weather": {
                "type": "api",
                "endpoint": "example"
            }
        }
    }

    settings = FlotillaSettings.from_dict(data)

    dumped = settings.model_dump()
    assert dumped["tools"]["weather"]["type"] == "api"
    assert dumped["tools"]["weather"]["endpoint"] == "example"
