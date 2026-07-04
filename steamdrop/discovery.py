import logging
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
import asyncio

logger = logging.getLogger(__name__)

class AirDropBrowser:
    def __init__(self):
        self.zeroconf = Zeroconf()
        self.discovered_devices = {}

    async def browse(self, timeout=10):
        browser = ServiceBrowser(self.zeroconf, "_airdrop._tcp.local.", self)
        await asyncio.sleep(timeout)
        browser.cancel()
        return self.discovered_devices

    def add_service(self, zeroconf: Zeroconf, type: str, name: str):
        info = zeroconf.get_service_info(type, name)
        if info:
            device_id = name.split(".")[0]
            addresses = [str(addr) for addr in info.parsed_addresses()]

            # Extract info from TXT records
            properties = {k.decode() if isinstance(k, bytes) else k:
                         v.decode() if isinstance(v, bytes) else v
                         for k, v in info.properties.items()}

            device_info = {
                "name": name,
                "addresses": addresses,
                "port": info.port,
                "properties": properties,
                "model": properties.get("model", "Unknown"),
                "flags": properties.get("flags", "0")
            }
            self.discovered_devices[device_id] = device_info
            logger.info(f"Discovered AirDrop device: {name} at {addresses}:{info.port}")

    def update_service(self, zeroconf: Zeroconf, type: str, name: str):
        self.add_service(zeroconf, type, name)

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str):
        device_id = name.split(".")[0]
        if device_id in self.discovered_devices:
            logger.info(f"Removed AirDrop device: {name}")
            del self.discovered_devices[device_id]

    def close(self):
        self.zeroconf.close()

async def _main():
    logging.basicConfig(level=logging.INFO)
    browser = AirDropBrowser()
    try:
        print("Browsing for AirDrop devices...")
        devices = await browser.browse()
        for dev_id, info in devices.items():
            print(f"Found: {info['name']} - {info['addresses']}:{info['port']} (Model: {info['model']})")
    finally:
        browser.close()

if __name__ == "__main__":
    asyncio.run(_main())
