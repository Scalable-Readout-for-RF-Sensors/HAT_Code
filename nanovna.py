#!/usr/bin/env python3
"""
DISCLAIMER:
-----------
This script is NOT original code from this team. It has been sourced and adapted from another
repository. All credit for the implementation belongs to the original authors.

This script provides a Python interface for controlling a NanoVNA device over serial, allowing
frequency sweeps, S-parameter data acquisition, visualization (e.g. Smith charts, log magnitude,
VSWR), and saving of measurement results in various formats.

Author: ttrftech (github.com/ttrftech/NanoVNA)
Adapted by: Djan Gural Tanova
"""
# Robust NanoVNA Python Interface (Improved)
import serial
import numpy as np
import pylab as pl
import struct
import time
from serial.tools import list_ports

VID = 0x0483
PID = 0x5740
REF_LEVEL = (1 << 9)


def getport():
    for device in list_ports.comports():
        if device.vid == VID and device.pid == PID:
            return device.device
    raise OSError("NanoVNA device not found")


class NanoVNA:
    def __init__(self, dev=None):
        self.dev = dev or getport()
        self.serial = None
        self._frequencies = None
        self.points = 101

    @property
    def frequencies(self):
        return self._frequencies

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.dev, timeout=2)

    def close(self):
        if self.serial:
            self.serial.close()
            self.serial = None

    def restart(self):
        print("[INFO] Restarting NanoVNA serial connection...")
        self.close()
        time.sleep(0.5)
        self.open()

    def is_ready(self):
        try:
            self.send_command("pause\r")
            self.send_command("resume\r")
            return True
        except Exception as e:
            print(f"[WARN] NanoVNA not ready: {e}")
            print(f"                                ", end="\r")
            return False

    def send_command(self, cmd):
        self.open()
        try:
            self.serial.reset_input_buffer()
            self.serial.write(cmd.encode())
            self.serial.readline()
        except Exception as e:
            print(f"[ERROR] Command failed: {cmd.strip()} — {e}")
            raise

    def fetch_data(self, timeout=3):
        """
        Fetches textual response from NanoVNA until 'ch>' or timeout.

        Returns:
            str: Raw data string received from the device.

        Raises:
            TimeoutError: If response doesn't complete in time.
        """
        result = []
        deadline = time.time() + timeout
        self.serial.timeout = 0.5  # set temporary per-line timeout

        while time.time() < deadline:
            try:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            except Exception as e:
                raise TimeoutError(f"[ERROR] Failed reading from NanoVNA: {e}")

            if not line:
                continue  # timeout hit on readline, try again

            result.append(line)

            if 'ch>' in line:
                break

        else:
            raise TimeoutError("[ERROR] Timeout waiting for NanoVNA 'ch>' prompt.")

        return '\n'.join(result)


    def set_frequencies(self, start=1e6, stop=900e6, points=None):
        if points:
            self.points = points
        self.set_sweep(start, stop)
        self._frequencies = np.linspace(start, stop, self.points)

    def set_sweep(self, start, stop):
        if start is not None:
            self.send_command("sweep start %d\r" % start)
        if stop is not None:
            self.send_command("sweep stop %d\r" % stop)

    def fetch_frequencies(self):
        self.send_command("frequencies\r")
        data = self.fetch_data()
        self._frequencies = np.array([float(line) for line in data.splitlines() if line.strip().replace('.', '').isdigit()])

    def data(self, array=0):
        self.send_command(f"data {array}\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                try:
                    d = line.strip().split(' ')
                    x.append(float(d[0]) + float(d[1]) * 1.j)
                except (ValueError, IndexError):
                    print(f"[WARN] Skipping invalid line: {line.strip()}", end="\r")
                    print(f"                                ", end="\r")
        return np.array(x)

    def send_scan(self, start, stop, points):
        self.send_command(f"scan {int(start)} {int(stop)} {points}\r")

    def scan(self):
        MAX_SEGMENT = self.points
        array0, array1 = [], []
        frequencies_used = []

        if self._frequencies is None:
            self.fetch_frequencies()

        freqs = self._frequencies
        total_points = len(freqs)
        offset = 0

        while offset < total_points:
            segment_freqs = freqs[offset:offset + MAX_SEGMENT]
            if len(segment_freqs) < 2:
                break  # skip incomplete segment

            seg_start = segment_freqs[0]
            seg_stop = segment_freqs[-1]
            length = len(segment_freqs)

            self.send_scan(seg_start, seg_stop, length)

            # Retry loop until data length matches expectation
            retry_limit = int(MAX_SEGMENT/10)
            for attempt in range(retry_limit):
                s0 = self.data(0)
                s1 = self.data(1)
                if len(s0) == length and len(s1) == length:
                    break
                print(f"[WARN] Incomplete data (attempt {attempt+1}): got {len(s0)}/{length} points. Retrying...", end="\r")
                print(f"                                                                                        ", end="\r")
                time.sleep(0.1)
            else:
                raise TimeoutError(f"Failed to get {length} points after {retry_limit} attempts.")

            array0.extend(s0)
            array1.extend(s1)
            frequencies_used.extend(np.linspace(seg_start, seg_stop, length))

            offset += MAX_SEGMENT

        self._frequencies = np.array(frequencies_used)
        self.resume()
        return (np.array(array0), np.array(array1))


    def pause(self):
        self.send_command("pause\r")

    def resume(self):
        self.send_command("resume\r")

    def logmag(self, x):
        pl.grid(True)
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, 20*np.log10(np.abs(x)))
