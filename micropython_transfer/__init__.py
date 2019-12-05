"""
Transfer for micropython boards based on a serial connection

@author Kevin Kratzer <kevin.kratzer@ghelia.com>
@version 1.0

Copyright (C) 2019 GHELIA Inc.
"""
from typing import List

from .serial_transmitter import SerialTransmitter

__version__ = '0.1.0'
__all__: List[str] = [
    'SerialTransmitter'
]
