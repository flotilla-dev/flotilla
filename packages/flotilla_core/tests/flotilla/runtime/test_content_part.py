import pytest
import json
from pydantic import ValidationError

from flotilla.runtime.content_part import (
    TextPart,
    StructuredPart,
    FilePart,
    ContentPartFactory,
)


# ============================================================
# Round-trip tests
# ============================================================


def test_text_part_round_trip():
    part = TextPart(text="hello", mime_type="text/plain")

    serialized = part.serialize()
    restored = ContentPartFactory.deserialize_part(serialized)

    assert part == restored


def test_structured_part_round_trip():
    part = StructuredPart(
        mime_type="application/json",
        data={"a": 1, "b": [1, 2]},
    )

    serialized = part.serialize()
    restored = ContentPartFactory.deserialize_part(serialized)

    assert part == restored


def test_file_part_round_trip():
    part = FilePart(
        url="https://example.com/file",
        mime_type="image/png",
        bytes=123,
        sha256="a" * 64,
    )

    serialized = part.serialize()
    restored = ContentPartFactory.deserialize_part(serialized)

    assert part == restored


# ============================================================
# Validation tests
# ============================================================


def test_text_part_invalid_mime():
    with pytest.raises(ValueError):
        TextPart(text="hello", mime_type="application/json")


def test_structured_part_invalid_mime():
    with pytest.raises(ValueError):
        StructuredPart(mime_type="text/plain", data={})


def test_file_part_invalid_sha():
    with pytest.raises(ValueError):
        FilePart(
            url="x",
            mime_type="image/png",
            sha256="invalid",
        )


# ============================================================
# Factory behavior
# ============================================================


def test_factory_missing_type():
    payload = json.dumps({"text": "hello"})
    with pytest.raises(ValueError):
        ContentPartFactory.deserialize_part(payload)


def test_factory_unknown_type():
    payload = json.dumps({"type": "unknown"})
    with pytest.raises(ValueError):
        ContentPartFactory.deserialize_part(payload)


def test_factory_invalid_json():
    with pytest.raises(ValueError):
        ContentPartFactory.deserialize_part("not-json")


# ============================================================
# Deterministic serialization
# ============================================================


def test_deterministic_serialization():
    part1 = StructuredPart(
        mime_type="application/json",
        data={"b": 2, "a": 1},
    )

    part2 = StructuredPart(
        mime_type="application/json",
        data={"a": 1, "b": 2},
    )

    assert part1.serialize() == part2.serialize()


# ============================================================
# Immutability
# ============================================================


def test_immutability():
    part = TextPart(text="hello", mime_type="text/plain")

    with pytest.raises(ValidationError):
        part.text = "changed"


# ============================================================
# Extra fields forbidden
# ============================================================


def test_extra_fields_forbidden():
    with pytest.raises(Exception):
        TextPart(text="hello", mime_type="text/plain", extra="bad")
