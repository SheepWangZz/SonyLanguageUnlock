"""Bounded MSC identity/version queries. No firmware upload or mode switch."""
import hashlib
import io
from pathlib import Path
import re
import struct
import time
from .i18n import UserError
from .usb_backend import get_usb_backend, backend_name
from pmca.usb.driver.generic import MscBbbDriver
from pmca.usb.sony import SonyMscExtCmdDevice, SonyExtCmdCamera, SonyUpdaterCamera


def validate_query(cmd, data, buffer_size):
    expected = SonyExtCmdCamera.ExtCmdHeader.pack(dataSize=0, cmd=1, direction=0).ljust(0x2000, b'\0')
    if cmd == 1 and data == expected and buffer_size == 0x2000:
        return
    for command in (SonyUpdaterCamera.CMD_INIT, SonyUpdaterCamera.CMD_QUERY_VERSION):
        expected = SonyUpdaterCamera.PacketHeader.pack(bodySize=0,
            protocolVersion=SonyUpdaterCamera.protocolVersion, commandId=command,
            responseId=0, sequenceNumber=0)
        if cmd == 0 and data == expected and buffer_size == SonyUpdaterCamera.BUFFER_SIZE:
            return
    raise ValueError('Detection command is not an approved identity/version query')


class ReadyDriver(MscBbbDriver):
    def sendCommand(self, command, failOnError=False):
        if command != bytes(6):
            raise ValueError('Only TEST UNIT READY is allowed')
        end = min(self.backend.deadline, time.monotonic() + 8)
        while time.monotonic() < end:
            sense = super().sendCommand(command, failOnError)
            if sense not in {(2, 4, 1), (6, 0x29, 0), (6, 0x28, 0)}:
                self.last_ready = sense
                return sense
            time.sleep(.25)
        raise UserError('busy_timeout')


class QueryDevice(SonyMscExtCmdDevice):
    def sendSonyExtCommand(self, cmd, data, bufferSize):
        validate_query(cmd, data, bufferSize)
        command = bytes([self.MSC_OC_ExtCmd]) + struct.pack('<I', cmd) + bytes(7)
        def exchange(read):
            while time.monotonic() < self.driver.backend.deadline:
                if read:
                    sense, result = self.driver.sendReadCommand(command, bufferSize)
                else:
                    sense = self.driver.sendWriteCommand(command, data)
                    result = None
                if sense != self.MSC_SENSE_DeviceBusy:
                    self._checkResponse(sense)
                    return result
                time.sleep(.25)
            raise UserError('busy_timeout')
        exchange(False)
        return exchange(True)


def query_info(driver, pid):
    device = QueryDevice(driver)
    device._checkResponse(driver.last_ready)
    info = SonyExtCmdCamera(device).getCameraInfo()
    updater = SonyUpdaterCamera(device)
    updater.init()
    version, _ = updater.getFirmwareVersion()
    if not re.fullmatch(r'\d+\.\d{2}', version):
        raise UserError('invalid_version')
    serial = bytes.fromhex(info.serial)
    if not serial or not any(serial):
        raise ValueError('Camera identity is missing')
    return {'model': info.modelName, 'version': version, 'pid': pid,
            'body_digest': hashlib.sha256(serial).hexdigest()}


def parse_service_info(version_bytes, backup):
    from pmca.backup import BackupFile
    if len(version_bytes) != 2 or any((v & 15) > 9 or (v >> 4) > 9 for v in version_bytes):
        raise UserError('invalid_version')
    version = '%x.%02x' % (version_bytes[1], version_bytes[0])
    if not 256 < len(backup) <= 4 * 1024 * 1024:
        raise ValueError('Invalid identity file size')
    parsed = BackupFile(io.BytesIO(backup))
    if not 256 <= parsed.size <= len(backup):
        raise ValueError('Invalid identity file layout')
    serial = parsed.getProperty(0x00e70003).data
    if not serial or len(serial) > 64 or not any(serial):
        raise ValueError('Camera identity is missing')
    return {'model': 'ILCE-7CM2', 'version': version, 'pid': 0x0e8a,
            'body_digest': hashlib.sha256(serial).hexdigest(),
            'detection_method': 'service-read-only'}


def read_service_info(log=lambda message: None, event=lambda *a, **kw: None, connector=None):
    from .transport import connect, VERSION, BACKUP
    connector = connector or connect
    state = {}
    try:
        event('service_connection')
        with connector(False, None, log, state, read_only=True) as camera:
            event('read_firmware_file')
            version = camera.read_file(VERSION, 4096)
            event('read_identity_file')
            backup = camera.read_file(BACKUP)
            result = parse_service_info(version, backup)
            event('identity_read_ok', model=result['model'], version=result['version'])
            event('return_to_normal_usb')
    finally:
        event('service_cleanup', normal_usb_return=state.get('normal_usb_return', False),
              write_attempts=state.get('write_attempts', []), connection_failure=state.get('failure_stage'),
              service_backend=state.get('service_backend'),
              service_stop_error=state.get('service_stop_error'),
              normal_usb_error=state.get('normal_usb_error'))
    if not state.get('normal_usb_return'):
        raise UserError('reconnect_required')
    return result


def _detect(log, event):
    import usb.core
    import usb.util
    import usb.backend.libusb1
    import libusb_package
    from pmca.usb.driver.generic.libusb import UsbBackend

    class Backend(UsbBackend):
        def __init__(self, dev):
            super().__init__(dev)
            self.deadline = time.monotonic() + 30
        def timeout(self):
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise UserError('busy_timeout')
            return max(1, min(5000, int(remaining * 1000)))
        def read(self, ep, length, timeout=None):
            return self.dev.read(ep, length, self.timeout()).tobytes()
        def write(self, ep, data):
            if self.dev.write(ep, data, self.timeout()) != len(data):
                raise IOError('Incomplete USB query; stopped without retry')

    backend = get_usb_backend()
    event('usb_backend', backend=backend_name())
    event('usb_enumeration')
    candidates = []
    devices = list(usb.core.find(find_all=True, idVendor=0x054c, backend=backend))
    try:
        for device in devices:
            event('usb_seen', pid=f'{device.idProduct:04x}')
            # The backend addresses interface 0 / alternate setting 0 only.
            interface = device.get_active_configuration()[(0, 0)]
            if interface.bInterfaceClass == 8 and interface.bInterfaceProtocol == 0x50:
                device.default_timeout = 3000
                event('product_descriptor', pid=f'{device.idProduct:04x}')
                product = usb.util.get_string(device, device.iProduct) or ''
                if product.startswith(('ILCE-', 'DSC-', 'ZV-', 'ILME-', 'HDR-', 'FDR-', 'NEX-', 'SLT-')):
                    candidates.append(device)
        if not candidates:
            raise UserError('no_camera')
        if len(candidates) != 1:
            raise UserError('multiple')
        camera = candidates[0]
        if camera.idProduct == 0x0e8a and usb.util.get_string(camera, camera.iProduct) == 'ILCE-7CM2':
            # Do not send SCSI or updater queries on this body. This route reads
            # only two fixed files through the previously used service protocol.
            usb.util.dispose_resources(camera)
            event('selected_service_readonly')
            log(UserError('service_detect'))
            return read_service_info(log, event)
        event('normal_msc_query')
        usb.util.claim_interface(camera, 0)
        return query_info(ReadyDriver(Backend(camera)), camera.idProduct)
    finally:
        for device in devices:
            usb.util.dispose_resources(device)


def detect(log=lambda message: None, report_root=None):
    from .workflow import state_root, write_json
    folder = Path(report_root) if report_root else state_root() / 'diagnostics'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder / ('detect-' + str(time.time_ns()) + '.json')
    report = {'file_writes_enabled': False, 'events': [], 'status': 'RUNNING'}
    def event(stage, **values):
        if stage != 'service_cleanup':
            report['stage'] = stage
        elif values.get('connection_failure') and report.get('stage') == 'service_connection':
            report['stage'] = values['connection_failure']
        report['events'].append({'stage': stage, **values})
        write_json(report_path, report)
    try:
        result = _detect(log, event)
        report.update(status='OK', model=result['model'], version=result['version'],
                      method=result.get('detection_method', 'normal-msc-query'))
        write_json(report_path, report)
        return result
    except Exception as exc:
        report.update(status='FAILED', error=str(exc), error_type=type(exc).__name__,
                      errno=getattr(exc, 'errno', None), backend_error=getattr(exc, 'backend_error_code', None))
        write_json(report_path, report)
        if getattr(exc, 'errno', None) in (32, 10060, 110) or getattr(exc, 'backend_error_code', None) in (-7, -9):
            raise UserError('usb_reconnect', stage=report.get('stage', 'USB')) from exc
        raise
    finally:
        log('检测记录：' + str(report_path))
