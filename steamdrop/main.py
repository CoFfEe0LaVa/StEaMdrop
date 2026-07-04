import argparse
import asyncio
import logging
import sys
import os
try:
    from steamdrop.discovery import AirDropBrowser
    from steamdrop.transfer import AirDropClient
    from steamdrop.ble_wakeup import AirDropWakeUp
except ImportError:
    from discovery import AirDropBrowser
    from transfer import AirDropClient
    from ble_wakeup import AirDropWakeUp

async def main():
    parser = argparse.ArgumentParser(description="SteamDrop: AirDrop from PC to iPhone")
    parser.add_argument("file", help="File to send")
    parser.add_argument("--target", help="Target device ID or name (optional)")
    parser.add_argument("--no-wakeup", action="store_true", help="Skip BLE wakeup")
    parser.add_argument("--timeout", type=int, default=10, help="Discovery timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not os.path.exists(args.file):
        print(f"Error: File {args.file} does not exist.")
        sys.exit(1)

    if not args.no_wakeup:
        wakeup = AirDropWakeUp()
        print("Sending BLE wakeup advertisement...")
        await wakeup.advertise()

    browser = AirDropBrowser()
    print(f"Browsing for AirDrop devices (timeout {args.timeout}s)...")
    try:
        devices = await browser.browse(timeout=args.timeout)
    finally:
        browser.close()

    if not devices:
        print("No AirDrop devices found. Make sure AirDrop is set to 'Everyone' on the target device.")
        sys.exit(1)

    print("\nDiscovered devices:")
    target_info = None
    for i, (dev_id, info) in enumerate(devices.items()):
        print(f"[{i}] {info['name']} (ID: {dev_id}, Model: {info['model']})")
        if args.target and (args.target == dev_id or args.target in info['name']):
            target_info = info

    if not target_info:
        if args.target:
            print(f"\nSpecified target '{args.target}' not found.")
            sys.exit(1)

        if len(devices) == 1:
            target_info = list(devices.values())[0]
            print(f"\nSelecting only available device: {target_info['name']}")
        else:
            try:
                choice = int(input("\nSelect device index to send to: "))
                target_info = list(devices.values())[choice]
            except (ValueError, IndexError):
                print("Invalid selection.")
                sys.exit(1)

    # Use the first available address (usually IPv6)
    target_host = target_info['addresses'][0]
    target_port = target_info['port']

    print(f"\nSending '{args.file}' to {target_info['name']} at {target_host}:{target_port}...")
    client = AirDropClient(target_host, target_port)

    print("Asking for permission...")
    if client.ask(args.file):
        print("Permission granted! Uploading file...")
        if client.upload(args.file):
            print("File sent successfully!")
        else:
            print("Upload failed.")
    else:
        print("Permission denied or request failed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
