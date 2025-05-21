from nanovna import NanoVNA
from switch import SwitchAdapter
import numpy as np
import os, datetime,typing

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

    def __init__(self, size:int=12, bit_width:int=5, bit_start:int=10, bit_padding:int=1):
        """
        Initializes the RFMultiplexer instance and configures the NanoVNA.

        Args:
            size (int): Number of ports. Default is 12.
            bit_width (int): Frequency width (MHz) of bit detection window. Default is 5.
            bit_start (int): Starting frequency (MHz) for low-bit band. Default is 10.
            bit_padding (int): Padding (MHz) between low and high bit bands. Default is 1.
        """
        self.size = size
        self.address_dict = {}
        self.bit_width = bit_width
        self.lo_start = bit_start
        self.bit_padding = bit_padding
        self.hi_start = bit_start + bit_width + bit_padding

        self.DATA_PATH = "./data"
        os.makedirs(self.DATA_PATH, exist_ok=True)

        self.vna = NanoVNA()

        lo = (self.lo_start - 2) * 1e6
        hi = (self.hi_start + self.bit_width) * 1e6
        self.vna.set_frequencies(start=lo, stop=hi, points=201)

        self.switch_adapter = SwitchAdapter()

    def _detect_bit(self, frequencies:np.typing.NDArray[typing.Any], s11:np.typing.NDArray[typing.Any]):
        """
        Analyzes S11 data to detect the presence of a '0' or '1' bit based on frequency dips.

        Args:
            frequencies (np.array): Frequency points of the measurement.
            s11 (np.array): S11 reflection data.

        Returns:
            int or None: Detected bit (0 or 1), or None if no bit detected.
        """
        s11_db = 20 * np.log10(np.abs(s11))
        dip_threshold = -10  # dB threshold for detecting a dip

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

    def read(self, port:int):
        """
        Reads the bit value from the specified port.

        Args:
            port (int): Port number to read from.

        Returns:
            int or None: Detected bit (0 or 1), or None if not detected.
        """
        self.switchPort(port)
        self.vna.resume()
        if self.vna.frequencies is not None:
            freqs = self.vna.frequencies 
        else:

            lo = (self.lo_start - 2) * 1e6
            hi = (self.hi_start + self.bit_width + 2) * 1e6
            self.vna.set_frequencies(start=lo, stop=hi, points=201)
            freqs = self.vna.frequencies 

        s11 = self.vna.scan()[0]
        bit = self._detect_bit(typing.cast(np.ndarray,freqs), typing.cast(np.ndarray,s11))
        self.address_dict[str(port)] = bit
        print(f"Bit: {bit}")
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

    def switchPort(self, port_no:int):
        """
        Set the PE42512 to activate the given port number (0-11 = RF1-RF12).
        """
        self.switch_adapter.switchPort(port_no)
        print(f"Switched to port: {port_no}", end="\r")

    def save(self, filename: str = "snapshot.s1p"):
        """
        Saves the current S-parameter data from the NanoVNA to a Touchstone (.s1p) file.

        Args:
            filename (str): Path to the output Touchstone file.
        """
        self.vna.fetch_frequencies()
        s11 = self.vna.scan()[0]
        network = self.vna.skrf_network(s11)
        network.write_touchstone(os.path.join(self.DATA_PATH, filename))
        print(f"[INFO] Snapshot saved to {filename}")

    def record(self, sweeps: int = 5):
        """
        Records multiple sweep snapshots and saves them as Touchstone files.

        Args:
            sweeps (int): Number of sweeps to record.
        """
        for i in range(sweeps):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sweep_{i+1}_{timestamp}.s1p"
            self.save(filename)
            print(f"[INFO] Sweep {i+1}/{sweeps} saved as {filename}")

    def close(self):
        self.switch_adapter.close()