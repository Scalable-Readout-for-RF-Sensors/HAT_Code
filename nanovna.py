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

import serial
import numpy as np
import pylab as pl
import struct
import time
from serial.tools import list_ports

# USB Vendor and Product ID for NanoVNA
VID = 0x0483
PID = 0x5740

# Automatically detect NanoVNA serial port
def getport() -> str:
    """
    Finds the connected NanoVNA device based on USB VID/PID.
    
    Returns:
        str: The system path to the detected serial device.

    Raises:
        OSError: If no device with the expected VID/PID is found.
    """
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device.device
    raise OSError("NanoVNA device not found")

# Reference level used for gamma computation
REF_LEVEL = (1 << 9)

class NanoVNA:
    """
    Class for interfacing with a NanoVNA over a serial connection.
    Provides methods for frequency sweep setup, measurement acquisition,
    and data plotting.
    """

    def __init__(self, dev=None):
        """
        Initializes the NanoVNA object and optionally connects to a specified device.

        Args:
            dev (str): Path to serial device (e.g., /dev/ttyUSB0 or COM3). If None, auto-detects.
        """
        self.dev = dev or getport()
        self.serial = None
        self._frequencies = None
        self.points = 101

    @property
    def frequencies(self):
        """Returns the frequency array currently set for sweeping."""
        return self._frequencies

    def set_frequencies(self, start=1e6, stop=900e6, points=None):
        """
        Sets the frequency sweep range and resolution.

        Args:
            start (float): Start frequency in Hz.
            stop (float): Stop frequency in Hz.
            points (int): Number of measurement points.
        """
        if points:
            self.points = points
        self._frequencies = np.linspace(start, stop, self.points)

    def open(self):
        """Opens the serial connection to the NanoVNA."""
        if self.serial is None:
            self.serial = serial.Serial(self.dev)

    def close(self):
        """Closes the serial connection to the NanoVNA."""
        if self.serial:
            self.serial.close()
        self.serial = None

    def send_command(self, cmd):
        """
        Sends a command to the NanoVNA.

        Args:
            cmd (str): Command string to send.
        """
        self.open()
        self.serial.write(cmd.encode())
        self.serial.readline()  # Discard the echoed line

    def set_sweep(self, start, stop):
        """Configures the sweep start and stop frequencies."""
        if start is not None:
            self.send_command(f"sweep start {int(start)}\r")
        if stop is not None:
            self.send_command(f"sweep stop {int(stop)}\r")

    def set_frequency(self, freq):
        """Sets the current frequency."""
        if freq is not None:
            self.send_command(f"freq {int(freq)}\r")

    def set_port(self, port):
        """Selects the measurement port (e.g., 0, 1)."""
        if port is not None:
            self.send_command(f"port {int(port)}\r")

    def set_gain(self, gain):
        """Sets the TX/RX gain."""
        if gain is not None:
            self.send_command(f"gain {int(gain)} {int(gain)}\r")

    def set_offset(self, offset):
        """Sets the internal measurement offset."""
        if offset is not None:
            self.send_command(f"offset {int(offset)}\r")

    def set_strength(self, strength):
        """Sets the TX signal strength."""
        if strength is not None:
            self.send_command(f"power {int(strength)}\r")

    def set_filter(self, filter):
        """Stores a local filter setting (not sent to device)."""
        self.filter = filter

    def fetch_data(self):
        """
        Fetches textual response from NanoVNA until the command prompt 'ch>' is detected.

        Returns:
            str: Raw data string received from the device.
        """
        result = ''
        line = ''
        while True:
            c = self.serial.read().decode('utf-8')
            if c == chr(13):
                continue
            line += c
            if c == chr(10):
                result += line
                line = ''
                continue
            if line.endswith('ch>'):
                break
        return result

    def fetch_buffer(self, freq=None, buffer=0):
        """
        Retrieves raw ADC buffer data.

        Args:
            freq (float): Optional frequency to set before capture.
            buffer (int): Buffer number (usually 0 or 1).

        Returns:
            np.ndarray: 1D array of raw 16-bit samples.
        """
        self.send_command(f"dump {buffer}\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                x.extend([int(d, 16) for d in line.strip().split(' ')])
        return np.array(x, dtype=np.int16)

    def fetch_rawwave(self, freq=None):
        """
        Retrieves paired ADC samples from reference and measured channels.

        Returns:
            tuple: (reference_samples, measured_samples) as numpy arrays.
        """
        if freq:
            self.set_frequency(freq)
            time.sleep(0.05)
        self.send_command("dump 0\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                x.extend([int(d, 16) for d in line.strip().split(' ')])
        return np.array(x[0::2], dtype=np.int16), np.array(x[1::2], dtype=np.int16)

    def fetch_array(self, sel):
        """
        Fetches a complex S-parameter array from the device.

        Args:
            sel (int): Array index (usually 0 or 1).

        Returns:
            np.ndarray: Complex array of S-parameters.
        """
        self.send_command(f"data {sel}\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                x.extend([float(d) for d in line.strip().split(' ')])
        return np.array(x[0::2]) + np.array(x[1::2]) * 1j

    def fetch_gamma(self, freq=None):
        """
        Fetches gamma (reflection coefficient) from the device.

        Returns:
            complex: Computed reflection coefficient.
        """
        if freq:
            self.set_frequency(freq)
        self.send_command("gamma\r")
        data = self.serial.readline()
        d = data.strip().split(' ')
        return (int(d[0]) + int(d[1]) * 1.j) / REF_LEVEL

    def reflect_coeff_from_rawwave(self, freq=None):
        """
        Computes reflection coefficient from raw waveforms using the Hilbert transform.

        Returns:
            complex: Reflection coefficient.
        """
        from scipy import signal
        ref, samp = self.fetch_rawwave(freq)
        refh = signal.hilbert(ref)
        return np.average(refh * samp / np.abs(refh) / REF_LEVEL)

    reflect_coeff = reflect_coeff_from_rawwave
    gamma = reflect_coeff_from_rawwave
    coefficient = reflect_coeff

    def resume(self):
        """Resumes NanoVNA measurements."""
        self.send_command("resume\r")

    def pause(self):
        """Pauses NanoVNA measurements."""
        self.send_command("pause\r")

    def scan_gamma0(self, port=None):
        """Scans and returns reflection coefficient from the active port using rawwave method."""
        self.set_port(port)
        return np.vectorize(self.gamma)(self.frequencies)

    def scan_gamma(self, port=None):
        """Scans and returns reflection coefficient using gamma command."""
        self.set_port(port)
        return np.vectorize(self.fetch_gamma)(self.frequencies)

    def data(self, array=0):
        """Fetches complex data array from the device."""
        self.send_command(f"data {array}\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                d = line.strip().split(' ')
                x.append(float(d[0]) + float(d[1]) * 1.j)
        return np.array(x)

    def fetch_frequencies(self):
        """Fetches frequency values from the device."""
        self.send_command("frequencies\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                x.append(float(line))
        self._frequencies = np.array(x)

    def send_scan(self, start=1e6, stop=900e6, points=None):
        """Instructs NanoVNA to perform a sweep over specified frequency range."""
        if points:
            self.send_command(f"scan {int(start)} {int(stop)} {points}\r")
        else:
            self.send_command(f"scan {int(start)} {int(stop)}\r")

    def scan(self):
        """
        Performs a full scan over all configured frequency points in segments.

        Returns:
            tuple: (array0, array1) of complex data
        """
        segment_length = 101
        array0 = []
        array1 = []
        frequencies_used = []

        if self._frequencies is None:
            self.fetch_frequencies()

        freqs = self._frequencies
        while len(freqs) > 0:
            length = min(segment_length, len(freqs))
            seg_start = freqs[0]
            seg_stop = freqs[length - 1]
            
            self.send_scan(seg_start, seg_stop, length)
            array0.extend(self.data(0))
            array1.extend(self.data(1))
            frequencies_used.extend(np.linspace(seg_start, seg_stop, length))

            freqs = freqs[segment_length:]

        self._frequencies = np.array(frequencies_used)
        self.resume()
        return (array0, array1)


    def capture(self):
        """
        Captures current screen display from NanoVNA as an image.

        Returns:
            PIL.Image: Captured display image.
        """
        from PIL import Image
        self.send_command("capture\r")
        b = self.serial.read(320 * 240 * 2)
        x = struct.unpack(">76800H", b)
        arr = np.array(x, dtype=np.uint32)
        arr = 0xFF000000 + ((arr & 0xF800) >> 8) + ((arr & 0x07E0) << 5) + ((arr & 0x001F) << 19)
        return Image.frombuffer('RGBA', (320, 240), arr, 'raw', 'RGBA', 0, 1)

    # -- Plotting Utilities (abbreviated comments below) --

    def logmag(self, x):
        """Plots log magnitude (dB)."""
        pl.grid(True)
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, 20 * np.log10(np.abs(x)))

    def linmag(self, x):
        """Plots linear magnitude."""
        pl.grid(True)
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, np.abs(x))

    def phase(self, x, unwrap=False):
        """Plots phase angle."""
        pl.grid(True)
        a = np.angle(x)
        if unwrap:
            a = np.unwrap(a)
        else:
            pl.ylim((-180, 180))
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, np.rad2deg(a))

    def delay(self, x):
        """Plots group delay estimation."""
        pl.grid(True)
        delay = -np.unwrap(np.angle(x)) / (2 * np.pi * np.array(self.frequencies))
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, delay)

    def groupdelay(self, x):
        """Plots numerical group delay."""
        pl.grid(True)
        gd = np.convolve(np.unwrap(np.angle(x)), [1, -1], mode='same')
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, gd)

    def vswr(self, x):
        """Plots Voltage Standing Wave Ratio."""
        pl.grid(True)
        vswr = (1 + np.abs(x)) / (1 - np.abs(x))
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, vswr)

    def polar(self, x):
        """Plots polar chart of complex reflection coefficients."""
        ax = pl.subplot(111, projection='polar')
        ax.grid(True)
        ax.set_ylim((0, 1))
        ax.plot(np.angle(x), np.abs(x))

    def tdr(self, x):
        """Performs time-domain reflectometry (TDR) analysis."""
        pl.grid(True)
        window = np.blackman(len(x))
        NFFT = 256
        td = np.abs(np.fft.ifft(window * x, NFFT))
        time = 1 / (self.frequencies[1] - self.frequencies[0])
        t_axis = np.linspace(0, time, NFFT)
        pl.plot(t_axis, td)
        pl.xlim(0, time)
        pl.xlabel("time (s)")
        pl.ylabel("magnitude")

    def smithd3(self, x):
        """Interactive Smith chart using mpld3 + twoport (requires browser)."""
        import mpld3
        import twoport as tp
        fig, ax = pl.subplots()
        sc = tp.SmithChart(show_cursor=True, labels=True, ax=ax)
        sc.plot_s_param(x)
        mpld3.display(fig)

    def skrf_network(self, x):
        """Converts data to a scikit-rf Network object."""
        import skrf as sk
        n = sk.Network()
        n.frequency = sk.Frequency.from_f(self.frequencies / 1e6, unit='mhz')
        n.s = x
        return n

    def smith(self, x):
        """Plots Smith chart using scikit-rf."""
        n = self.skrf_network(x)
        n.plot_s_smith()
        return n
    
    def save_plot():
        pl.save("fig.png")


# -- Plotting raw data (for testing) --

def plot_sample0(samp):
    N = min(len(samp), 256)
    fs = 48000
    pl.subplot(211)
    pl.grid()
    pl.plot(samp)
    pl.subplot(212)
    pl.grid()
    pl.psd(samp, N, window=pl.blackman(N), Fs=fs)

def plot_sample(ref, samp):
    N = min(len(samp), 256)
    fs = 48000
    pl.subplot(211)
    pl.grid()
    pl.plot(ref)
    pl.plot(samp)
    pl.subplot(212)
    pl.grid()
    pl.psd(ref, N, window=pl.blackman(N), Fs=fs)
    pl.psd(samp, N, window=pl.blackman(N), Fs=fs)
