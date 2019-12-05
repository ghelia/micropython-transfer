# V2
"""
Helper for storing files on a micropython microcontroller
Based on code from the uPyLoader project. See the NOTICE file for details

Modified by: Kevin Kratzer <kevin.kratzer@ghelia.com>
@version 1.0

Modifications Copyright (C) 2019 GHELIA Inc.
"""
import sys
import time

from ubinascii import a2b_base64


def _read_timeout(cnt, timeout_ms=2000):
    time_support = "ticks_ms" in dir(time)
    s_time = time.ticks_ms() if time_support else 0
    data = sys.stdin.read(cnt)
    if len(data) != cnt or (time_support and time.ticks_diff(time.ticks_ms(), s_time) > timeout_ms):
        return None
    return data


def _upload():
    suc = False
    with open("file_name.py", "wb") as target_file:
        while True:
            received_data = _read_timeout(3)
            if not received_data or received_data[0] != "#":
                sys.stdout.write("#2")
                break
            cnt = int(received_data[1:3])
            if cnt == 0:
                suc = True
                break
            received_data = _read_timeout(cnt)
            if received_data:
                target_file.write(a2b_base64(received_data))
                sys.stdout.write("#1")
            else:
                sys.stdout.write("#3")
                break
    sys.stdout.write("#0" if suc else "#4")


_upload()
