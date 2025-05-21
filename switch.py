from gpiozero import DigitalOutputDevice

class SwitchAdapter:
    def __init__(self):
        self.pins = {
            'LS': DigitalOutputDevice(24),
            'V1': DigitalOutputDevice(23),
            'V2': DigitalOutputDevice(22),
            'V3': DigitalOutputDevice(27),
            'V4': DigitalOutputDevice(17),
        }

    def _set_control_pins(self, ls, v4, v3, v2, v1):
        self.pins['LS'].value = ls
        self.pins['V1'].value = v1
        self.pins['V2'].value = v2
        self.pins['V3'].value = v3
        self.pins['V4'].value = v4
        #time.sleep(0.002)  # optional: allow hardware settling time

    def switchPort(self, port_no: int):
        """
        Set the PE42512 to activate the given port number (0–11 = RF1–RF12).
        """
        if not (0 <= port_no <= 11):
            raise ValueError("Port number must be between 0 and 11")

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

        ls = 0
        v4, v3, v2, v1 = control_bits[port_no]
        self._set_control_pins(ls, v4, v3, v2, v1)
    
    def close(self):
        """
        Gracefully release all GPIO pins.
        """
        for pin in self.pins.values():
            pin.close()
