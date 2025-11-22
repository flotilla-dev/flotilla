import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--target",
        action="store",
        default="core",
        choices=["core", "example", "all"],
        help="Choose which tests to run: core, example, or all"
    )

def pytest_collection_modifyitems(config, items):
    target = config.getoption("--target")
    if target == "core":
        skip_example = pytest.mark.skip(reason="Skipping example app tests")
        for item in items:
            if "example" in item.keywords:
                item.add_marker(skip_example)
        # Set coverage for core framework only
        config.option.cov_source = ["agents", "models", "config", "utils"]
    elif target == "example":
        skip_core = pytest.mark.skip(reason="Skipping core framework tests")
        for item in items:
            if "example" not in item.keywords:
                item.add_marker(skip_core)
        # Set coverage for example app only
        config.option.cov_source = ["example_app"]
    else:  # "all"
        config.option.cov_source = ["agents", "models", "config", "utils", "example_app"]
