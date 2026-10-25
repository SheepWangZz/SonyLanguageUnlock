"""Fixed-path, exact-byte, one-attempt service transport. No ID1 or shell API."""
from contextlib import contextmanager
import struct
import time
from . import settings, fonts
from .usb_backend import get_usb_backend, find_service_devices
from pmca.usb.driver.generic import GenericUsbDriver

HEADER = struct.Struct('<IHHBBBB')
MAX = 0x100000
VERSION = '/setting/updater/dat4'
BACKUP = '/setting/Backup.bin'
READ = struct.pack('<HHB', 0x603, 5, 1)
WRITE = struct.pack('<HHI', 0x603, 4, 2)
FILE_READ = struct.pack('<HH', 0x1001, 0x11) + b'\0\xff\0'
FILE_WRITE = struct.pack('<HH', 0x1001, 0x10) + b'\0\xff\0'
_last_service_exit = None
SERVICE_COOLDOWN = 30


def select(path):
    return struct.pack('<HH', 0x1001, 0xf) + b'\0/tmp/jiritsu/../..' + path.encode('ascii') + b'\0'


class FileResultError(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(f'相机文件服务返回 0x{result:08x}')


class Guard(GenericUsbDriver):
    def __init__(self, backend, chinese, assets=None, read_only=False):
        super().__init__(backend)
        self.chinese = bool(chinese)
        self.read_only = bool(read_only)
        if self.read_only and (chinese or assets):
            raise ValueError('只读检测禁止字体访问')
        self.assets = fonts.validate(assets) if assets is not None else {}
        if self.assets and not chinese:
            raise ValueError('未选择中文，禁止加载字体')
        paths = [VERSION, BACKUP] + (list(fonts.FONTS) if chinese else [])
        self.selects = {select(p): p for p in paths}
        self.selected = self.armed = self.pending = None
        self.attempts = []
        self.poisoned = False

    def arm_pdt(self, before, after, phase, attrs):
        settings.validate_candidate(before, after, self.chinese, phase, attrs)
        if phase == 'restore' and 'enable' not in self.attempts:
            raise ValueError('保护恢复顺序不正确')
        self._arm(phase, WRITE + after, None)

    def arm_font(self, path):
        if path not in self.assets or self.selected != path:
            raise ValueError('字体写入路径未授权')
        self._arm(path, FILE_WRITE + self.assets[path], path)

    def _arm(self, key, request, path):
        if self.read_only:
            raise ValueError('只读检测禁止写入')
        if self.poisoned or self.armed or self.pending or key in self.attempts:
            raise ValueError('禁止重试或重叠写入')
        self.armed = (key, request, path)

    def write(self, data, ep=0):
        raw = bytes(data)
        if self.poisoned or ep or len(raw) < HEADER.size:
            raise ValueError('连接已停止或帧无效')
        n, fn, seq, *flags = HEADER.unpack(raw[:12])
        body = raw[12:]
        if fn != 0x40 or any(flags) or not n or len(body) != min(n, MAX):
            raise ValueError('发送帧不符合白名单')
        next_pending = None
        selected = self.selected
        if self.pending:
            key, request, expected_seq, offset = self.pending
            if seq != expected_seq or n != len(request) - offset or body != request[offset:offset + MAX]:
                raise ValueError('后续帧内容被更改')
            offset += len(body)
            if offset < len(request):
                next_pending = (key, request, seq, offset)
        elif n == len(body) and body in self.selects and self.armed is None:
            selected = self.selects[body]
        elif n == len(body) and body == FILE_READ and selected is not None and self.armed is None:
            pass
        elif n == len(body) and body == READ and self.armed is None and not self.read_only:
            pass
        elif self.armed:
            key, request, path = self.armed
            if n != len(request) or body != request[:MAX] or (path and selected != path):
                raise ValueError('写入字节不符合批准的候选')
            self.armed = None
            self.attempts.append(key)  # Consumed BEFORE USB, including a failed send.
            if len(body) < n:
                next_pending = (key, request, seq, len(body))
        else:
            raise ValueError('命令被拦截：只允许固定读回与本次批准的写入')
        try:
            result = super().write(raw, ep)
        except Exception:
            self.poisoned = True
            raise
        self.selected, self.pending = selected, next_pending
        return result


class Camera:
    def __init__(self, guard):
        self.guard = guard
        self.sequence = 1

    def _read_exact(self, n):
        out, empty = bytearray(), 0
        while len(out) < n:
            want = min(0x8000, n - len(out))
            part = self.guard.read(want)
            if len(part) > want:
                raise ValueError('读取块过长')
            if not part:
                empty += 1
                if empty > 64:
                    raise ValueError('读取无进展')
            else:
                empty = 0
                out.extend(part)
        return bytes(out)

    def exchange(self, request, limit):
        seq = self.sequence
        try:
            for offset in range(0, len(request), MAX):
                self.guard.write(HEADER.pack(len(request)-offset, 0x40, seq, 0, 0, 0, 0) + request[offset:offset+MAX])
            out = bytearray()
            for _ in range(8):
                n, fn, reply_seq, version, micon, offset, status = HEADER.unpack(self._read_exact(12))
                if fn != 0x40 or reply_seq != seq or version not in (0, 3) or micon or offset or status:
                    raise ValueError('相机回复帧异常')
                count = min(n, MAX)
                if len(out) + count > limit:
                    raise ValueError('相机回复超过大小限制')
                out.extend(self._read_exact(count))
                if n <= MAX:
                    self.sequence = (seq + 1) & 0xffff
                    return bytes(out)
            raise ValueError('相机回复分段过多')
        except Exception:
            self.guard.poisoned = True
            raise

    def command(self, request):
        response = self.exchange(request, 4)
        if len(response) != 4:
            self.guard.poisoned = True
            raise ValueError('缺少文件服务状态码')
        result, = struct.unpack('<I', response)
        if result:
            raise FileResultError(result)

    def read_file(self, path, limit=settings.LIMIT):
        self.command(select(path))
        response = self.exchange(FILE_READ, limit + 4)
        if len(response) < 4:
            self.guard.poisoned = True
            raise ValueError('缺少文件读取状态码')
        result, = struct.unpack_from('<I', response)
        if result:
            raise FileResultError(result)
        return response[4:]

    def memory(self):
        return self.exchange(READ, settings.LIMIT)

    def write_settings(self, before, candidate, phase, attrs):
        self.guard.arm_pdt(before, candidate, phase, attrs)
        # PDT response is not a Jiritsu result code. Verify through fresh snapshots.
        self.exchange(WRITE + candidate, 64)

    def write_font(self, path):
        self.command(select(path))
        self.guard.arm_font(path)
        self.command(FILE_WRITE + self.guard.assets[path])


@contextmanager
def connect(chinese, assets, log, state, read_only=False):
    global _last_service_exit
    import usb.core
    import usb.util
    import usb.backend.libusb1
    import libusb_package
    from pmca.usb.driver.generic.libusb import UsbBackend
    from pmca.usb.sony import SonySenserAuthDevice

    # A normal USB descriptor can return before the camera's service subsystem
    # is ready for another authentication. Never immediately re-enter it.
    if _last_service_exit is not None:
        remaining = SERVICE_COOLDOWN - (time.monotonic() - _last_service_exit)
        if remaining > 0:
            log('等待相机完成上次服务连接退出，随后继续。')
            time.sleep(remaining)

    class Backend(UsbBackend):
        def read(self, ep, length, timeout=None):
            return self.dev.read(ep, length, timeout or 10000).tobytes()

        def write(self, ep, data):
            count = self.dev.write(ep, data, 10000)
            if count != len(data):
                raise IOError('USB 写入不完整，禁止自动重试')

    backend = get_usb_backend()

    def find(pid):
        if pid == 0x0336:
            devices, selected_backend = find_service_devices(backend)
            if devices:
                state['service_backend'] = selected_backend
        else:
            devices = list(usb.core.find(find_all=True, idVendor=0x054c,
                                        idProduct=pid, backend=backend))
        if len(devices) > 1:
            raise RuntimeError('请只连接一台 Sony 相机')
        return next((d for d in devices if d.idProduct == pid), None)

    def wait(pid, seconds=20):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            d = find(pid)
            if d is not None:
                return d
            time.sleep(.25)
        raise TimeoutError('相机 USB 接口未出现；请检查连接和驱动')

    def driver(device):
        usb.util.claim_interface(device, 0)
        return GenericUsbDriver(Backend(device))

    current = auth = None
    entered = False
    try:
        state['connection_stage'] = 'find_normal_usb'
        current = find(0x0e8a)
        if current is None:
            raise RuntimeError('未找到普通 MSC 相机；请开机、连接 USB 并选择大容量存储')
        if usb.util.get_string(current, current.iProduct) != 'ILCE-7CM2':
            raise RuntimeError('仅支持 ILCE-7CM2')
        log('已确认 ILCE-7CM2，正在切换服务连接。')
        state['connection_stage'] = 'normal_open'
        auth = SonySenserAuthDevice(driver(current))
        entered = True
        state['connection_stage'] = 'normal_start'
        auth.start()
        state['connection_stage'] = 'normal_authenticate'
        auth.authenticate()
        usb.util.dispose_resources(current)
        current = auth = None
        state['connection_stage'] = 'wait_service_usb'
        current = wait(0x0336)
        state['connection_stage'] = 'service_open'
        d = driver(current)
        auth = SonySenserAuthDevice(d)
        state['connection_stage'] = 'service_start'
        auth.start()
        state['connection_stage'] = 'service_authenticate'
        auth.authenticate()
        guard = Guard(d.backend, chinese, assets, read_only=read_only)
        log('服务连接已就绪。')
        state['connection_stage'] = 'service_ready'
        try:
            yield Camera(guard)
        finally:
            state['write_attempts'] = guard.attempts
    except Exception:
        state['failure_stage'] = state.get('connection_stage')
        raise
    finally:
        if auth is not None:
            try:
                auth.stop()
            except Exception as exc:
                state['service_stop_error'] = str(exc)
        if current is not None:
            usb.util.dispose_resources(current)
        if entered:
            try:
                normal = wait(0x0e8a, 15)
                state['normal_usb_return'] = True
                usb.util.dispose_resources(normal)
            except Exception as exc:
                state['normal_usb_return'] = False
                state['normal_usb_error'] = str(exc)
            _last_service_exit = time.monotonic()
