# -*- coding: utf-8 -*-

from __future__ import print_function

import platform

import opensearchpy

print(
    "{} {}; opensearchpy {}".format(
        platform.python_implementation(),
        platform.python_version(),
        opensearchpy.VERSION,
    )
)
