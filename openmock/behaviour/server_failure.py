"""
Simulate server failure
"""

from functools import wraps
from asyncio import iscoroutinefunction


__ENABLED = False


def enable():
    """
    Enable server failure
    """
    global __ENABLED
    __ENABLED = True


def disable():
    """
    Disable server failure
    """
    global __ENABLED
    __ENABLED = False


def server_failure(f):
    """
    Decorator to simulate server failure
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if __ENABLED:
            return {"status_code": 500, "error": "Internal Server Error"}
        return f(*args, **kwargs)

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        if __ENABLED:
            return {"status_code": 500, "error": "Internal Server Error"}
        return await f(*args, **kwargs)

    return async_wrapper if iscoroutinefunction(f) else wrapper
