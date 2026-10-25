from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from language_tool import detection, settings
from language_tool.transport import Guard, HEADER, READ, WRITE, VERSION, BACKUP
from language_tool.i18n import UserError


class Backend:
    def getEndpoints(self):
        return [SimpleNamespace(bmAttributes=2, bEndpointAddress=0x81),
                SimpleNamespace(bmAttributes=2, bEndpointAddress=2)]
    def write(self, *args):
        pytest.fail('Forbidden write reached USB')


@pytest.mark.parametrize('payload', [READ, WRITE + b'test'])
def test_readonly_guard_blocks_pdt_commands(payload):
    guard = Guard(Backend(), False, read_only=True)
    with pytest.raises(ValueError):
        guard.write(HEADER.pack(len(payload), 0x40, 1, 0, 0, 0, 0) + payload)
    assert guard.attempts == []


def test_readonly_cannot_arm_a_write():
    guard = Guard(Backend(), False, read_only=True)
    with pytest.raises(ValueError, match='只读'):
        guard._arm('enable', WRITE + b'test', None)


def test_service_detection_reads_only_two_files_and_returns_normal(backup):
    paths = []
    class Camera:
        def read_file(self, path, *args):
            paths.append(path)
            return b'\x01\x02' if path == VERSION else backup
    @contextmanager
    def connection(chinese, assets, log, state, read_only=False):
        assert read_only and not chinese and assets is None
        yield Camera()
        state.update(normal_usb_return=True, write_attempts=[])
    result = detection.read_service_info(connector=connection)
    assert result['version'] == '2.01'
    assert result['body_digest'] == settings.identity(backup)
    assert paths == [VERSION, BACKUP]


def test_service_detection_refuses_incomplete_exit(backup):
    @contextmanager
    def connection(chinese, assets, log, state, read_only=False):
        yield SimpleNamespace(read_file=lambda path, *args: b'\x01\x02' if path == VERSION else backup)
        state['normal_usb_return'] = False
    with pytest.raises(UserError) as error:
        detection.read_service_info(connector=connection)
    assert error.value.key == 'reconnect_required'


def test_a7c2_does_not_send_normal_msc_queries(monkeypatch):
    import usb.core
    import usb.util
    import usb.backend.libusb1
    class Device:
        idProduct, iProduct = 0x0e8a, 1
        def get_active_configuration(self):
            return {(0, 0): SimpleNamespace(bInterfaceClass=8, bInterfaceProtocol=0x50)}
    monkeypatch.setattr(detection, 'get_usb_backend', lambda: object())
    monkeypatch.setattr(usb.core, 'find', lambda **kwargs: [Device()])
    monkeypatch.setattr(usb.util, 'get_string', lambda *args: 'ILCE-7CM2')
    monkeypatch.setattr(usb.util, 'dispose_resources', lambda *args: None)
    monkeypatch.setattr(detection, 'query_info', lambda *args: pytest.fail('Normal MSC query used'))
    monkeypatch.setattr(detection, 'read_service_info', lambda *args: {'method': 'readonly'})
    assert detection._detect(lambda *args: None, lambda *args, **kw: None) == {'method': 'readonly'}


def test_failed_stage_is_preserved_in_diagnostic_log(tmp_path, monkeypatch):
    import json
    def fail(log, event):
        event('read_firmware_file')
        event('service_cleanup', normal_usb_return=True)
        raise OSError(32, 'Pipe error')
    monkeypatch.setattr(detection, '_detect', fail)
    with pytest.raises(UserError) as error:
        detection.detect(report_root=tmp_path)
    assert error.value.key == 'usb_reconnect'
    record = json.loads(next(tmp_path.glob('*.json')).read_text())
    assert record['stage'] == 'read_firmware_file'
    assert record['errno'] == 32 and record['status'] == 'FAILED'
