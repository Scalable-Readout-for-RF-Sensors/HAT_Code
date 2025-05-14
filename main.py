import argparse
from nanovna import NanoVNA
import numpy as np

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

    def switchPort(self, port_no):
        """
        Switches the NanoVNA to the specified port.

        Args:
            port_no (int): Port number to activate.
        """
        return

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive RF multiplexer interface.")
    parser.add_argument("--ports", type=int, default=12, help="Number of ports to scan (default: 12)")
    parser.add_argument("--bit_width", type=int, default=10, help="Bit width in MHz (default: 10)")
    parser.add_argument("--bit_start", type=int, default=40, help="Start frequency of low range in MHz (default: 40)")
    parser.add_argument("--bit_padding", type=int, default=5, help="Padding between low and high in MHz (default: 5)")
    args = parser.parse_args()

    mux = RFMultiplexer(
        size=args.ports,
        bit_width=args.bit_width,
        bit_start=args.bit_start,
        bit_padding=args.bit_padding
    )

    print("RF Multiplexer Interface Ready.")
    print("Commands:")
    print("  run <port>  - read bit at given port number")
    print("  run all     - read all ports")
    print("  quit        - exit application\n")

    while True:
        cmd = input(">>> ").strip().lower()
        if cmd == "quit":
            print("Exiting...")
            break
        elif cmd.startswith("run "):
            _, _, arg = cmd.partition(" ")
            if arg == "all":
                results = mux.readAll()
                print("\nRead All Ports:")
                for port, bit in results.items():
                    print(f"Port {port}: Bit {bit}")
            elif arg.isdigit():
                port = int(arg)
                if 0 <= port < mux.size:
                    bit = mux.read(port)
                    print(f"Port {port}: Bit {bit}")
                else:
                    print(f"[ERROR] Port {port} is out of range (0-{mux.size - 1}).")
            else:
                print("[ERROR] Invalid argument to 'run'. Use a port number or 'all'.")
        else:
            print("[ERROR] Unknown command. Use 'run <port>', 'run all', or 'quit'.")
