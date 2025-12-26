import pytest

from flotilla.container.contributors.base_contributors import ContributorGroup
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.config.settings import FlotillaSettings

class TestContext:
    def __init__(self):
        self.events = []

class ContributorA:
    def contribute(self, container, context):
        context.events.append("A")

    def validate(self, container, context):
        context.events.append("A_validate")


class ContributorB:
    def contribute(self, container, context):
        context.events.append("B")

    def validate(self, container, context):
        context.events.append("B_validate")

class TestContributorGroup(ContributorGroup[TestContext]):
    name = "test-group"
    priority = 0

    def create_context(self) -> TestContext:
        return TestContext()

    def create_contributors(self):
        return [
            ContributorA(),
            ContributorB(),
        ]

def test_contributor_group_creates_single_context():
    group = TestContributorGroup()

    ctx1 = group._context
    ctx2 = group._context

    assert ctx1 is ctx2

def test_contributor_group_passes_shared_context():
    group = TestContributorGroup()
    container = FlotillaContainer(
        FlotillaSettings.from_dict({})
    )

    group.contribute(container)

    assert group._context.events == ["A", "B"]

def test_contributor_group_validation_order():
    group = TestContributorGroup()
    container = FlotillaContainer(
        FlotillaSettings.from_dict({})
    )

    group.contribute(container)
    group.validate(container)

    assert group._context.events == [
        "A",
        "B",
        "A_validate",
        "B_validate",
    ]


def test_contributor_group_does_not_leak_context_to_container():
    group = TestContributorGroup()
    container = FlotillaContainer(
        FlotillaSettings.from_dict({})
    )

    group.contribute(container)

    assert not hasattr(container, "context")
    assert not hasattr(container, "events")


