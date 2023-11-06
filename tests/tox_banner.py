import platform

import opensearchpy

print(
    "{} {}; opensearchpy {}".format(
        platform.python_implementation(),
        platform.python_version(),
        opensearchpy.VERSION,
    )
)
