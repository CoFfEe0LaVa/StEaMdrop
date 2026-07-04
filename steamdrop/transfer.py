import io
import os
import plistlib
import logging
import requests
import gzip
import tarfile # CPIO is hard in standard python, using tar as fallback or find a way.
# Actually, I'll use a simple CPIO implementation if possible or just use what OpenDrop did.
# Wait, OpenDrop used libarchive. I've installed libarchive-c.
import libarchive
import socket

logger = logging.getLogger(__name__)

class AirDropClient:
    def __init__(self, target_host, target_port=8770):
        self.target_host = target_host
        self.target_port = target_port
        self.session = requests.Session()
        # AirDrop usually uses HTTPS with self-signed certs or specific certs.
        # For "Everyone" mode, it might be simpler or we might need to skip verification.
        self.session.verify = False
        self.base_url = f"https://{target_host}:{target_port}"

    def _send_plist(self, endpoint, data):
        plist_data = plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
        headers = {
            "Content-Type": "application/x-apple-binary-plist",
            "User-Agent": "AirDrop/1.0",
        }
        url = f"{self.base_url}{endpoint}"
        try:
            # We use IPv6 addresses often, so we need to handle brackets if needed
            if ":" in self.target_host and not self.target_host.startswith("["):
                url = f"https://[{self.target_host}]:{self.target_port}{endpoint}"

            response = self.session.post(url, data=plist_data, headers=headers, timeout=30)
            if response.status_code == 200:
                return True, plistlib.loads(response.content)
            else:
                logger.error(f"Request to {endpoint} failed with status {response.status_code}")
                return False, None
        except Exception as e:
            logger.error(f"Error sending plist to {endpoint}: {e}")
            return False, None

    def ask(self, filename, computer_name="SteamDrop PC", model_name="MacBookPro15,1"):
        # We need a unique SenderID, usually a random 12-char hex string
        sender_id = os.urandom(6).hex()

        file_size = os.path.getsize(filename)
        base_name = os.path.basename(filename)

        ask_data = {
            "SenderComputerName": computer_name,
            "SenderModelName": model_name,
            "SenderID": sender_id,
            "BundleID": "com.apple.finder",
            "ConvertMediaFormats": False,
            "Files": [
                {
                    "FileName": base_name,
                    "FileSize": file_size,
                    "FileIsDirectory": False,
                }
            ]
        }

        success, response = self._send_plist("/Ask", ask_data)
        return success

    def upload(self, filename):
        # AirDrop expects a gzipped CPIO archive
        archive_path = f"{filename}.cpio.gz"

        # Using libarchive-c to create CPIO
        with libarchive.file_writer(archive_path, 'cpio', 'gzip') as archive:
            archive.add_file(filename)

        with open(archive_path, "rb") as f:
            archive_data = f.read()

        # Clean up temporary archive
        os.remove(archive_path)

        headers = {
            "Content-Type": "application/octet-stream",
            "User-Agent": "AirDrop/1.0",
        }

        url = f"{self.base_url}/Upload"
        if ":" in self.target_host and not self.target_host.startswith("["):
            url = f"https://[{self.target_host}]:{self.target_port}/Upload"

        try:
            response = self.session.post(url, data=archive_data, headers=headers, timeout=60)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python transfer.py <target_ip> <file_path>")
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG)
    client = AirDropClient(sys.argv[1])
    if client.ask(sys.argv[2]):
        print("Permission granted (or at least /Ask succeeded), uploading...")
        if client.upload(sys.argv[2]):
            print("Upload successful!")
        else:
            print("Upload failed.")
    else:
        print("Ask failed.")
