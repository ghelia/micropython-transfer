"""
Module for realizing Micropython controller file transfer and communciation.
Based on code from the uPyLoader project. See the NOTICE file for details

Modified by: Kevin Kratzer <kevin.kratzer@ghelia.com>
@version 1.0

Modifications Copyright (C) 2019 GHELIA Inc.
"""
import base64
import os
import time
from typing import List, Optional, Union

import serial

UPLOAD_FILE_NAME = '__upload_0c19c2b6e0a34223afe5b.py'


class SerialTransmitter:
    """
    Facilitate simple file transfer to micropython based boards via a serial connection

    The SerialTransmitter must be used in a with statement e.g.:
    with SerialTransmitter(port) as transmitter:
        transmitter.upload('/home/user/example.py')

    Args:
        port (str): The serial port on which the controller can be accessed
    """
    def __init__(self, port: str):
        self.__port: str = port
        self.__serial_connection: Optional[serial.Serial] = None
        self.__base_send_delay: float = 0.03

    def __enter__(self):
        self.__serial_connection = SerialTransmitter.__open_serial_connection(self.__port)
        # Give board time to boot
        for _ in range(20):
            try:
                self._read_to_next_prompt(2)
            except TimeoutError:
                self.send_control_character("c")
        self.__send_upload_file()
        return self

    def __exit__(self, *_):
        self.__remove_upload_file()
        self.__serial_connection.close()
        self.__serial_connection = None

    @property
    def _serial_connection(self) -> serial.Serial:
        assert self.__serial_connection, 'SerialTransmitter must be used in a with statement'
        return self.__serial_connection

    @staticmethod
    def __open_serial_connection(port: str) -> serial.Serial:
        serial_connection = serial.Serial(None, 115200, timeout=0, write_timeout=0.2)
        serial_connection.dtr = False
        serial_connection.rts = True
        serial_connection.port = port
        serial_connection.open()
        time.sleep(1)
        serial_connection.rts = False
        return serial_connection

    def create_file(self, content: bytes, file_name: str):
        """
        Create a file from an utf-8 encoded data buffer
        Args:
            content (byte): utf-8 encoded data which will be stored in the file
            file_name (str): The filename for the newly created file on the controller
        """
        self.run_file(UPLOAD_FILE_NAME, "file_name=\"{}\"".format(file_name))
        self._flush_input()
        self._send_file(content)

    def upload(self, file_path: str):
        """
        Upload a file to the controller
        Args:
            file_path (str): The file path to be uploaded and stored on the controller
        """
        file_name = os.path.basename(file_path)
        with open(file_path, 'rb') as source:
            self.create_file(source.read(), file_name)

    def run_file(self, file_name: str, globals_init: str = ""):
        """
        Execute a file on the controller
        Args:
            file_name (str): The file name to be executed which is stored on the controller
            globals_init (str): Initializier prior to script execution
        """
        self._send_start_paste()
        if globals_init:
            self._send_line(globals_init, "\r")
        self._send_line("with open(\"{}\") as f:".format(file_name))
        self._send_line("    exec(f.read(), globals())")
        self._send_end_paste()

    def send_control_character(self, character: str):
        """
        Send a control character like ctrl+c
        Args:
            character (str): The control character e.g. c for ctrl+c
        """
        self._send_character(chr(ord(character) - ord("a") + 1))

    def _send_file(self, data: bytes):
        serial_connection = self._serial_connection
        # Split data into smaller chunks
        idx = 0
        # Using chunks of 48 bytes, encoded chunk should be at most 64 bytes
        chunk_size = 48
        total_len = len(data)
        while idx < total_len:
            chunk = data[idx:idx + chunk_size]
            # Encode data to prevent special REPL sequences
            en_chunk = base64.b64encode(chunk)
            serial_connection.write(
                b"".join([b"#", str(len(en_chunk)).zfill(2).encode("ascii"), en_chunk]))
            ack = self._read_with_timeout(2)

            error = None
            if not ack:
                error = "Device failed to respond in specified timeout."
            elif ack == b"#2":
                error = "Device didn't receive next message in time or message header corrupt."
            elif ack == b"#3":
                error = "Device didn't receive as much data as was indicated in the message header."
            elif ack != b"#1":
                error = "Error in protocol. Expected #1 but device replied with:\n{}.".format(
                    ack.decode(errors='ignore'))

            if error:
                error += "\n\nLast message was:\n{}.".format(chunk.decode(errors='ignore'))
                raise ConnectionError(error)

            idx += len(chunk)

        # Mark end and check for success
        serial_connection.write(b"#00")
        check = self._read_with_timeout(2)

        if not check:
            raise ConnectionError("Device failed to respond in specified timeout.")
        if check != b"#0":
            raise ConnectionError("Error in protocol. Expected #0 but device replied with: {}."
                                  .format(check.decode(errors='ignore')))

    def _read_with_timeout(self, count: int, timeout_s: float = 2.0) -> Optional[bytes]:
        serial_connection = self._serial_connection
        period = 0.005
        data = bytearray()
        for _ in range(0, int(timeout_s / period)):
            rec = serial_connection.read(count - len(data))
            if rec:
                data.extend(rec)
                if len(data) == count:
                    return bytes(data)
            time.sleep(period)

        return None

    def _flush_input(self):
        serial_connection = self._serial_connection
        while serial_connection.read(100):
            pass

    def __send_upload_file(self):
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'upload.py')
        with open(file_path, encoding='utf-8') as source:
            data = source.read()
            data = data.replace("file_name.py", UPLOAD_FILE_NAME)
            self.__paste_lines(data.split("\n"))
        with open(file_path, encoding='utf-8') as source:
            self._send_file(source.read().replace('"file_name.py"', 'file_name').encode('utf-8'))

    def __remove_upload_file(self):
        self.__paste_lines(['import os', f'os.remove("{UPLOAD_FILE_NAME}")'])

    def __paste_lines(self, lines: List[str]):
        self._send_start_paste()
        for line in lines:
            self._send_line(line, "\r")
        self._send_end_paste()
        self._flush_input()

    def _get_send_delay(self, transmitted_content: Union[str, bytes]) -> float:
        return min(1, max(
            self.__base_send_delay,
            (len(transmitted_content) >> 6)*self.__base_send_delay))

    def _send_line(self, line_text: str, ending: str = "\r\n"):
        assert isinstance(line_text, str)
        assert isinstance(ending, str)
        serial_connection = self._serial_connection
        serial_connection.write((line_text + ending).encode('utf-8'))
        serial_connection.flush()
        time.sleep(self._get_send_delay(line_text))

    def _send_character(self, char: str):
        assert isinstance(char, str)

        self._serial_connection.write(char.encode('utf-8'))
        time.sleep(self._get_send_delay(char))

    def _send_start_paste(self):
        self._send_character("\5")

    def _send_end_paste(self):
        self._send_character("\4")

    def _read_to_next_prompt(self, timeout: float = 5.0):
        serial_connection = self._serial_connection
        received_data = b""
        start_time = time.time()
        while len(received_data) < 4 or received_data[-4:] != b">>> ":
            if (time.time() - start_time) >= timeout:
                raise TimeoutError()
            received_data += serial_connection.read(1)
        return received_data.decode("utf-8", errors="replace")
