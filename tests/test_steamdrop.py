import pytest
from unittest.mock import MagicMock, patch
import os
import io
import plistlib
import asyncio
from steamdrop.discovery import AirDropBrowser
from steamdrop.transfer import AirDropClient

@pytest.mark.asyncio
async def test_discovery():
    with patch('steamdrop.discovery.Zeroconf'), \
         patch('steamdrop.discovery.ServiceBrowser'):
        browser = AirDropBrowser()

        # Simulate finding a service
        mock_info = MagicMock()
        mock_info.parsed_addresses.return_value = ["192.168.1.10"]
        mock_info.port = 8770
        mock_info.properties = {b"model": b"iPhone12,1"}

        with patch.object(browser.zeroconf, 'get_service_info', return_value=mock_info):
            browser.add_service(browser.zeroconf, "_airdrop._tcp.local.", "test-device._airdrop._tcp.local.")

        assert "test-device" in browser.discovered_devices
        assert browser.discovered_devices["test-device"]["model"] == "iPhone12,1"

def test_transfer_ask():
    # Create a dummy file
    with open("test_file.txt", "w") as f:
        f.write("test content")

    try:
        with patch('steamdrop.transfer.requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = plistlib.dumps({"ReceiverComputerName": "Test iPhone"})
            mock_post.return_value = mock_response

            client = AirDropClient("192.168.1.10")
            success = client.ask("test_file.txt")

            assert success is True
            mock_post.assert_called()
    finally:
        if os.path.exists("test_file.txt"):
            os.remove("test_file.txt")

def test_transfer_upload():
    # Dummy file
    with open("test_file.txt", "w") as f:
        f.write("test content")

    try:
        with patch('steamdrop.transfer.requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            client = AirDropClient("192.168.1.10")
            success = client.upload("test_file.txt")

            assert success is True
            mock_post.assert_called()
    finally:
        if os.path.exists("test_file.txt"):
            os.remove("test_file.txt")
