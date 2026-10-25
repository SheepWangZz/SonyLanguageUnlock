from types import SimpleNamespace
import struct
import time
import pytest
from language_tool.detection import query_info, validate_query
from pmca.usb.sony import SonyExtCmdCamera, SonyUpdaterCamera


@pytest.mark.parametrize('command', [0x10, 0x30, 0x40, 0x100, 0x200])
def test_detection_blocks_firmware_commands(command):
    raw = SonyUpdaterCamera.PacketHeader.pack(bodySize=0, protocolVersion=0x100,
        commandId=command, responseId=0, sequenceNumber=0)
    with pytest.raises(ValueError, match='approved'):
        validate_query(0, raw, 512)


def test_identity_version_query_without_firmware_writes():
    class Driver:
        backend = SimpleNamespace(deadline=time.monotonic()+10)
        def __init__(self):
            self.commands = []
        def reset(self):
            pass
        def sendCommand(self, command):
            assert command == bytes(6)
            self.last_ready = (0, 0, 0)
            return self.last_ready
        def sendWriteCommand(self, command, data):
            self.command, self.payload = command, data
            self.commands.append((command, data))
            return (0, 0, 0)
        def sendReadCommand(self, command, size):
            assert command == self.command
            group = struct.unpack_from('<I', command, 1)[0]
            if group == 1:
                name = b'ILCE-7CM2'
                body = bytes(8) + bytes([len(name)]) + name + bytes(5) + b'ABCD'
                raw = SonyExtCmdCamera.ExtCmdHeader.pack(dataSize=len(body), cmd=1, direction=1) + body
            else:
                header = SonyUpdaterCamera.PacketHeader.unpack(self.payload)
                if header.commandId == 1:
                    body = bytes(20)
                else:
                    assert header.commandId == 0x20
                    body = struct.pack('<HHHH', 1, 2, 0, 0)
                raw = SonyUpdaterCamera.PacketHeader.pack(bodySize=len(body), protocolVersion=0x100,
                    commandId=header.commandId, responseId=1, sequenceNumber=0) + body
            return (0, 0, 0), raw
    driver = Driver()
    result = query_info(driver, 0x0e8a)
    assert result['model'] == 'ILCE-7CM2' and result['version'] == '2.01'
    assert len(result['body_digest']) == 64 and 'serial' not in result
    assert len(driver.commands) == 3
