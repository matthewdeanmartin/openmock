import base64
import random
import string

DEFAULT_OPENSEARCH_ID_SIZE = 20
CHARSET_FOR_OPENSEARCH_ID = string.ascii_letters + string.digits

DEFAULT_OPENSEARCH_SEARCHRESULTPHASE_COUNT = 6


def get_random_id(size=DEFAULT_OPENSEARCH_ID_SIZE):
    """Generate a random id"""
    return "".join(
        random.choice(CHARSET_FOR_OPENSEARCH_ID) for _ in range(size)  # nosec
    )


def get_random_scroll_id(size=DEFAULT_OPENSEARCH_SEARCHRESULTPHASE_COUNT):
    """Generate a random scroll id"""
    return base64.b64encode("".join(get_random_id() for _ in range(size)).encode())


def extract_ignore_as_iterable(params):
    """Extracts the value of the ignore parameter as iterable"""
    ignore = params.get("ignore", ())
    if isinstance(ignore, int):
        ignore = (ignore,)
    return ignore
