import argparse
from rf_mux import RFMultiplexer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive RF multiplexer interface.")
    parser.add_argument("--ports", type=int, default=12, help="Number of ports to scan (default: 12)")
    parser.add_argument("--bit_width", type=int, default=5, help="Bit width in MHz (default: 5)")
    parser.add_argument("--bit_start", type=int, default=10, help="Start frequency of low range in MHz (default: 10)")
    parser.add_argument("--bit_padding", type=int, default=1, help="Padding between low and high in MHz (default: 1)")
    args = parser.parse_args()

    mux = RFMultiplexer(
        size=args.ports,
        bit_width=args.bit_width,
        bit_start=args.bit_start,
        bit_padding=args.bit_padding
    )

    print("RF Multiplexer Interface Ready.")
    print("Commands:")
    print("  record <sweeps>   - record given number of sweeps as touchstone files")
    print("  read <port>  - read bit at given port number")
    print("  read all     - read all ports")
    print("  save - save current sweep as a touchstone file")
    print("  switch <port> - switch to specified port only")
    print("  quit        - exit application\n")

    while True:
        cmd = input(">>> ").strip().lower()
        if cmd == "quit":
            print("Exiting...")
            mux.close()
            break
        elif cmd.startswith("read "):
            _, _, arg = cmd.partition(" ")
            if arg == "all":
                results = mux.readAll()
                print("\nRead All Ports:")
                for port, bit in results.items():
                    print(f"Port {port+1}: Bit {bit}")
            elif arg.isdigit():
                port = int(arg)
                if 0 <= port < mux.size:
                    bit = mux.read(port-1)
                    print(f"Port {port}: Bit {bit}")
                else:
                    print(f"[ERROR] Port {port} is out of range (0-{mux.size - 1}).")
            else:
                print("[ERROR] Invalid argument to 'read'. Use a port number or 'all'.")
        elif cmd.startswith("switch "):
            _, _, arg = cmd.partition(" ")
            if arg.isdigit():
                port = int(arg)
                if 0 <= port <= mux.size:
                    mux.switchPort(port-1)
                    print(f"Switched to port {port}")
                else:
                    print(f"[ERROR] Port {port} is out of range (0-{mux.size}).")
            else:
                print("[ERROR] Invalid argument to 'switch'. Use a port number.")
        elif cmd.startswith("record "):
            _, _, arg = cmd.partition(" ")
            if arg.isdigit():
                sweeps = int(arg)
                if 0 <= sweeps:
                    print(f"Recording for {sweeps} sweeps...")
                    mux.record(sweeps)
                else:
                    print(f"[ERROR] Number of Sweeps invalid.")
            else:
                print("[ERROR] Invalid argument to 'record'. Use a number.")
        elif cmd.startswith("save"):
            print("Taking snapshot...")
            mux.save()
        else:
            print("[ERROR] Unknown command. Use 'read <port>', 'switch <port>', 'read all', 'record <sweeps>', 'save', or 'quit'.")