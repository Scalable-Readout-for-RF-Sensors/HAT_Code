from nanovna import NanoVNA
import numpy as np
import RPi.GPIO as GPIO

class RFMultiplexer:
    """
    A class to interface with an RF multiplexer using a NanoVNA for detecting digital bits 
    encoded in RF frequency dips.

    Attributes:
        size (int): Number of ports on the multiplexer.
        address_dict (dict): Stores detected bit values for each port.
        bit_width (int): Width of the frequency band used to detect each bit.
        lo_start (int): Starting frequency (in MHz) of the low-bit detection band.
        bit_padding (int): Frequency spacing (in MHz) between low and high bit detection bands.
        hi_start (int): Starting frequency (in MHz) of the high-bit detection band.
        vna (NanoVNA): Instance of the NanoVNA for performing measurements.
    """

    def __init__(self, size=12, bit_width=10, bit_start=40, bit_padding=5):
        """
        Initializes the RFMultiplexer instance and configures the NanoVNA.

        Args:
            size (int): Number of ports. Default is 12.
            bit_width (int): Frequency width (MHz) of bit detection window. Default is 10.
            bit_start (int): Starting frequency (MHz) for low-bit band. Default is 40.
            bit_padding (int): Padding (MHz) between low and high bit bands. Default is 5.
        """
        self.size = size
        self.address_dict = {}
        self.bit_width = bit_width
        self.lo_start = bit_start
        self.bit_padding = bit_padding
        self.hi_start = bit_start + bit_width + bit_padding

        self.vna = NanoVNA()
        self.vna.open()

        lo = (self.lo_start - 2) * 1e6
        hi = (self.hi_start + self.bit_width + 2) * 1e6
        self.vna.set_frequencies(start=lo, stop=hi, points=201)

        # GPIO setup
        self.LS_PIN = 18
        self.V1_PIN = 16
        self.V2_PIN = 15
        self.V3_PIN = 13
        self.V4_PIN = 11

        GPIO.setmode(GPIO.BCM)
        for pin in [self.LS_PIN, self.V1_PIN, self.V2_PIN, self.V3_PIN, self.V4_PIN]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

    def _set_control_pins(self, ls, v4, v3, v2, v1):
        GPIO.output(self.LS_PIN, GPIO.HIGH if ls else GPIO.LOW)
        GPIO.output(self.V1_PIN, GPIO.HIGH if v1 else GPIO.LOW)
        GPIO.output(self.V2_PIN, GPIO.HIGH if v2 else GPIO.LOW)
        GPIO.output(self.V3_PIN, GPIO.HIGH if v3 else GPIO.LOW)
        GPIO.output(self.V4_PIN, GPIO.HIGH if v4 else GPIO.LOW)

    def switchPort(self, port_no):
        """
        Set the PE42512 to activate the given port number (0-11 = RF1-RF12).
        """
        if not (0 <= port_no <= 11):
            raise ValueError("Port number must be between 0 and 11")

        # Truth table matches ports 0–11 to V4 V3 V2 V1 under LS = 0
        control_bits = [
            [0, 0, 0, 0],  # Port 0 (RF1)
            [1, 0, 0, 0],  # Port 1 (RF2)
            [0, 1, 0, 0],  # Port 2 (RF3)
            [1, 1, 0, 0],  # Port 3 (RF4)
            [0, 0, 1, 0],  # Port 4 (RF5)
            [1, 0, 1, 0],  # Port 5 (RF6)
            [0, 1, 1, 0],  # Port 6 (RF7)
            [1, 1, 1, 0],  # Port 7 (RF8)
            [0, 0, 0, 1],  # Port 8 (RF9)
            [1, 0, 0, 1],  # Port 9 (RF10)
            [0, 1, 0, 1],  # Port 10 (RF11)
            [1, 1, 0, 1],  # Port 11 (RF12)
        ]

        # LS must be 0 to use standard binary control mode
        ls = 0
        v4, v3, v2, v1 = control_bits[port_no]
        self._set_control_pins(ls, v4, v3, v2, v1)

    def _detect_bit(self, frequencies, s11):
        """
        Analyzes S11 data to detect the presence of a '0' or '1' bit based on frequency dips.

        Args:
            frequencies (np.array): Frequency points of the measurement.
            s11 (np.array): S11 reflection data.

        Returns:
            int or None: Detected bit (0 or 1), or None if no bit detected.
        """
        s11_db = 20 * np.log10(np.abs(s11))
        dip_threshold = -5  # dB threshold for detecting a dip

        lo_range = (self.lo_start * 1e6, (self.lo_start + self.bit_width) * 1e6)
        hi_range = (self.hi_start * 1e6, (self.hi_start + self.bit_width) * 1e6)

        lo_mask = (frequencies >= lo_range[0]) & (frequencies <= lo_range[1])
        hi_mask = (frequencies >= hi_range[0]) & (frequencies <= hi_range[1])

        lo_dip = np.min(s11_db[lo_mask])
        hi_dip = np.min(s11_db[hi_mask])

        if lo_dip <= dip_threshold:
            return 0
        elif hi_dip <= dip_threshold:
            return 1
        else:
            return None

    def read(self, port):
        """
        Reads the bit value from the specified port.

        Args:
            port (int): Port number to read from.

        Returns:
            int or None: Detected bit (0 or 1), or None if not detected.
        """
        self.switchPort(port)
        self.vna.resume()
        freqs = self.vna.frequencies
        s11 = self.vna.data(0)
        bit = self._detect_bit(freqs, s11)
        self.address_dict[str(port)] = bit
        return bit

    def readAll(self):
        """
        Reads bit values from all ports and updates the address dictionary.

        Returns:
            dict: Mapping of port numbers to detected bits.
        """
        results = {}
        for port in range(self.size):
            bit = self.read(port)
            results[port] = bit
        self.address_dict = results
        return results
