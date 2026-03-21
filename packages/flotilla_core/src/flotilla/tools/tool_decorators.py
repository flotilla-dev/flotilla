# flotilla/tools/decorators.py


# decorators.py

_TOOL_MARKER = object()


def tool_call(func):
    func.__flotilla_tool__ = _TOOL_MARKER
    return func
