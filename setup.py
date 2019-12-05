"""
Micropython Transfer

@author Kevin Kratzer <kevin.kratzer@ghelia.com>
@version 2.0

Copyright (C) 2019 GHELIA Inc.
"""

import re

from setuptools import setup

with open('micropython_transfer/__init__.py') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


setup(
    name="micropython_transfer",
    version=version,
    description="Library for transferring files to micropython based "
                "boards using a serial connection",
    url="https://github.com/ghelia/micropython-transfer",
    install_requires=[
        'pyserial==3.4'
    ],
    packages=['micropython_transfer']
)
