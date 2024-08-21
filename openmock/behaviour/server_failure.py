"""
Simulate server failure
"""

from functools import wraps

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
    def decorated(*args, **kwargs):
        if __ENABLED:
            response = {"status_code": 500, "error": "Internal Server Error"}
        else:
            response = f(*args, **kwargs)
        return response

    return decorated
