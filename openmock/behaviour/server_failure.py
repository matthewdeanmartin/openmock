"""
Simulate server failure
"""

import inspect
from functools import wraps
from typing import Any, Callable


class ServerFailure:
    """
    Simulation of server failure
    """

    def __init__(self) -> None:
        self.__enabled = False

    def enable(self) -> None:
        """
        Enable server failure
        """
        self.__enabled = True

    def disable(self) -> None:
        """
        Disable server failure
        """
        self.__enabled = False

    def is_enabled(self) -> bool:
        """
        Check if server failure is enabled
        """
        return self.__enabled

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator to simulate server failure
        """

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.__enabled:
                return {"status_code": 500, "error": "Internal Server Error"}
            return f(*args, **kwargs)

        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.__enabled:
                return {"status_code": 500, "error": "Internal Server Error"}
            return await f(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(f) else wrapper


# Create a singleton instance to be used as a decorator and manager
server_failure = ServerFailure()

# Backwards compatibility for module-level functions
enable = server_failure.enable
disable = server_failure.disable
is_enabled = server_failure.is_enabled
