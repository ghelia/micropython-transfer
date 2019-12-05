# micropython-transfer

Library for transferring files to micropython based boards using a serial connection

## Target Python

3.6.4 <= Python Version <= 3.6.9

## Usage

```python
from glob import glob
from micropython_transfer import SerialTransmitter


device = '/dev/ttyACM0'  # declare your device here

with SerialTransmitter(device) as transmitter:
    for file_to_copy in glob('copy/*'):
        print(f'Uploading {file_to_copy}')
        transmitter.upload(file_to_copy)
```

## Static Code Analysis

```bash
pip install tox
tox
```
