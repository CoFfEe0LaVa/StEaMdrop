import logging
from zeroconf import ServiceBrowser, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf
import asyncio

logger = logging.getLogger(__name__)

class AirDropBrowser:
    def __init__(self):
        self.aiozc = AsyncZeroconf()
        self.discovered_devices = {}

    async def browse(self, timeout=10):
        browser = ServiceBrowser(self.aiozc.zeroconf, "_airdrop._tcp.local.", self)
        await asyncio.sleep(timeout)
        browser.cancel()
        return self.discovered_devices

    def add_service(self, zeroconf, type, name):
        # We need to use the event loop to get service info asynchronously
        asyncio.ensure_future(self._async_add_service(type, name))

    async def _async_add_service(self, type, name):
        info = await self.aiozc.async_get_service_info(type, name)
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

    def update_service(self, zeroconf, type, name):
        asyncio.ensure_future(self._async_add_service(type, name))

    def remove_service(self, zeroconf, type, name):
        device_id = name.split(".")[0]
        if device_id in self.discovered_devices:
            logger.info(f"Removed AirDrop device: {name}")
            del self.discovered_devices[device_id]

    async def close(self):
        await self.aiozc.async_close()

async def _main():
    logging.basicConfig(level=logging.INFO)
    browser = AirDropBrowser()
    try:
        print("Browsing for AirDrop devices...")
        devices = await browser.browse()
        for dev_id, info in devices.items():
            print(f"Found: {info['name']} - {info['addresses']}:{info['port']} (Model: {info['model']})")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(_main())
