import lgpio

class SwitchAdapter:
    def __init__(self):
        self.pins = {
            'LS': 18,
            'V1': 16,
            'V2': 15,
            'V3': 13,
            'V4': 11,
        }

        self.h = lgpio.gpiochip_open(0)
        for pin in self.pins.values():
            lgpio.gpio_claim_output(self.h, pin, 0)

    def _set_control_pins(self, ls, v4, v3, v2, v1):
        lgpio.gpio_write(self.h, self.pins['LS'], ls)
        lgpio.gpio_write(self.h, self.pins['V1'], v1)
        lgpio.gpio_write(self.h, self.pins['V2'], v2)
        lgpio.gpio_write(self.h, self.pins['V3'], v3)
        lgpio.gpio_write(self.h, self.pins['V4'], v4)

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