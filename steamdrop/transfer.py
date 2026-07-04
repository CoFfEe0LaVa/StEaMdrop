import io
import os
import plistlib
import logging
import requests
import gzip

logger = logging.getLogger(__name__)

def create_cpio_newc(filename):
    """
    Creates a simple CPIO archive in 'newc' format containing one file.
    AirDrop expects this format.
    """
    def pad(data, alignment):
        p = len(data) % alignment
        if p == 0: return b''
        return b'\x00' * (alignment - p)

    with open(filename, 'rb') as f:
        content = f.read()

    size = len(content)
    name = os.path.basename(filename)
    namesize = len(name) + 1 # include null terminator
    mode = 0o100644 # Regular file

    # newc header: 6 chars magic + 13 fields * 8 chars hex
    # magic: 070701
    # fields: ino, mode, uid, gid, nlink, mtime, filesize, devmajor, devminor, rdevmajor, rdevminor, namesize, check
    header = f"070701{0:08x}{mode:08x}{0:08x}{0:08x}{1:08x}{0:08x}{size:08x}{0:08x}{0:08x}{0:08x}{0:08x}{namesize:08x}{0:08x}"

    archive = header.encode('ascii') + name.encode('ascii') + b'\x00'
    archive += pad(archive, 4)
    archive += content
    archive += pad(archive, 4)

    # Trailer
    trailer_name = "TRAILER!!!"
    trailer_namesize = len(trailer_name) + 1
    trailer_header = f"070701{0:08x}{0:08x}{0:08x}{0:08x}{1:08x}{0:08x}{0:08x}{0:08x}{0:08x}{0:08x}{0:08x}{trailer_namesize:08x}{0:08x}"
    archive += trailer_header.encode('ascii') + trailer_name.encode('ascii') + b'\x00'
    archive += pad(archive, 4)

    # Final padding to 512 bytes is often done but maybe not strictly required for newc
    return archive

class AirDropClient:
    def __init__(self, target_host, target_port=8770):
        self.target_host = target_host
        self.target_port = target_port
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = f"https://{target_host}:{target_port}"

    def _send_plist(self, endpoint, data):
        plist_data = plistlib.dumps(data, fmt=plistlib.FMT_BINARY)
        headers = {
            "Content-Type": "application/x-apple-binary-plist",
            "User-Agent": "AirDrop/1.0",
        }
        url = f"{self.base_url}{endpoint}"
        if ":" in self.target_host and not self.target_host.startswith("["):
            url = f"https://[{self.target_host}]:{self.target_port}{endpoint}"

        try:
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
        try:
            cpio_data = create_cpio_newc(filename)
            archive_data = gzip.compress(cpio_data)
        except Exception as e:
            logger.error(f"Error creating CPIO archive: {e}")
            return False

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
        print("Permission granted, uploading...")
        if client.upload(sys.argv[2]):
            print("Upload successful!")
        else:
            print("Upload failed.")
    else:
        print("Ask failed.")
