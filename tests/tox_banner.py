import platform

import opensearchpy

print(
    f"{platform.python_implementation()} {platform.python_version()}; opensearchpy {opensearchpy.VERSION}"
)
