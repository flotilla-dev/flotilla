from typing import Any, Callable


def _route(method: str, path: str, **kwargs: Any):
    def decorator(func: Callable):
        if hasattr(func, "__flotilla_route__"):
            raise ValueError("Route already defined on this method")

        func.__flotilla_route__ = {
            "http_method": method,
            "path": path,
            "kwargs": kwargs,
        }
        return func

    return decorator


class routes:

    @staticmethod
    def get(path: str, **kwargs: Any):
        return _route("GET", path, **kwargs)

    @staticmethod
    def post(path: str, **kwargs: Any):
        return _route("POST", path, **kwargs)

    @staticmethod
    def put(path: str, **kwargs: Any):
        return _route("PUT", path, **kwargs)

    @staticmethod
    def delete(path: str, **kwargs: Any):
        return _route("DELETE", path, **kwargs)
