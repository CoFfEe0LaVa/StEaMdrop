import unittest
from unittest.mock import MagicMock, patch
import os
import io
import plistlib
from steamdrop.discovery import AirDropBrowser
from steamdrop.transfer import AirDropClient

class TestSteamDrop(unittest.TestCase):

    @patch('steamdrop.discovery.Zeroconf')
    @patch('steamdrop.discovery.ServiceBrowser')
    def test_discovery(self, mock_browser, mock_zeroconf):
        browser = AirDropBrowser()

        # Simulate finding a service
        mock_info = MagicMock()
        mock_info.parsed_addresses.return_value = ["192.168.1.10"]
        mock_info.port = 8770
        mock_info.properties = {b"model": b"iPhone12,1"}
        mock_zeroconf.get_service_info.return_value = mock_info

        browser.add_service(mock_zeroconf, "_airdrop._tcp.local.", "test-device._airdrop._tcp.local.")

        self.assertIn("test-device", browser.discovered_devices)
        self.assertEqual(browser.discovered_devices["test-device"]["model"], "iPhone12,1")

    @patch('steamdrop.transfer.requests.Session.post')
    def test_transfer_ask(self, mock_post):
        # Create a dummy file
        with open("test_file.txt", "w") as f:
            f.write("test content")

        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = plistlib.dumps({"ReceiverComputerName": "Test iPhone"})
            mock_post.return_value = mock_response

            client = AirDropClient("192.168.1.10")
            success = client.ask("test_file.txt")

            self.assertTrue(success)
            mock_post.assert_called()
        finally:
            if os.path.exists("test_file.txt"):
                os.remove("test_file.txt")

    @patch('steamdrop.transfer.requests.Session.post')
    def test_transfer_upload(self, mock_post):
        # Dummy file
        with open("test_file.txt", "w") as f:
            f.write("test content")

        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            client = AirDropClient("192.168.1.10")
            success = client.upload("test_file.txt")

            self.assertTrue(success)
            mock_post.assert_called()
        finally:
            if os.path.exists("test_file.txt"):
                os.remove("test_file.txt")

if __name__ == '__main__':
    unittest.main()
