import argparse
from rf_mux import RFMultiplexer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive RF multiplexer interface.")
    parser.add_argument("--ports", type=int, default=12, help="Number of ports to scan (default: 12)")
    parser.add_argument("--bit_width", type=int, default=10, help="Bit width in MHz (default: 10)")
    parser.add_argument("--bit_start", type=int, default=1, help="Start frequency of low range in MHz (default: 1)")
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
    print("  switch <port> - switch to specified port only")
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
        elif cmd.startswith("switch "):
            _, _, arg = cmd.partition(" ")
            if arg.isdigit():
                port = int(arg)
                if 0 <= port < mux.size:
                    mux.switchPort(port)
                    print(f"Switched to port {port}")
                else:
                    print(f"[ERROR] Port {port} is out of range (0-{mux.size - 1}).")
            else:
                print("[ERROR] Invalid argument to 'switch'. Use a port number.")
        else:
            print("[ERROR] Unknown command. Use 'run <port>', 'switch <port>', 'run all', or 'quit'.")