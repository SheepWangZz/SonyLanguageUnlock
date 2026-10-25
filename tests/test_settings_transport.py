import struct
from types import SimpleNamespace
import pytest
from language_tool import settings, fonts
from language_tool.transport import Guard, Camera, HEADER, MAX, READ, WRITE, FILE_READ, FILE_WRITE, VERSION, select


class Backend:
    def __init__(self):
        self.writes, self.reply, self.fail = [], bytearray(), False
    def getEndpoints(self):
        return [SimpleNamespace(bmAttributes=2, bEndpointAddress=p) for p in (0x81, 2)]
    def write(self, ep, raw):
        self.writes.append(bytes(raw))
        if self.fail:
            raise TimeoutError('short or failed USB')
    def read(self, ep, n, timeout=None):
        data = bytes(self.reply[:n])
        del self.reply[:n]
        return data


def frame(request, sequence=1):
    return HEADER.pack(len(request), 0x40, sequence, 0, 0, 0, 0) + request[:MAX]


@pytest.mark.parametrize('chinese', [False, True])
def test_only_language_bytes_checksum_and_tail_preserved(backup, chinese):
    attrs = settings.attributes(backup)
    first = settings.patch(backup, chinese, 'enable', attrs)
    second = settings.patch(first, chinese, 'restore', attrs)
    settings.verify(second, chinese, attrs)
    b = settings.parse(backup)
    assert second[b.size:] == backup[b.size:]
    assert settings.parse(second).getProperty(0xe70002) == b.getProperty(0xe70002)
    assert settings.identity(second) == settings.identity(backup)


def test_non_target_candidate_rejected(backup):
    attrs = settings.attributes(backup)
    candidate = settings.patch(backup, False, 'enable', attrs)
    b = settings.parse(candidate)
    b.setProperty(0xe70002, b'R')
    b.updateChecksum()
    with pytest.raises(ValueError, match='范围以外'):
        settings.validate_candidate(backup, b.file.getvalue(), False, 'enable', attrs)


@pytest.mark.parametrize('payload', [struct.pack('<HHB', 0x603, 15, 1),
    struct.pack('<HH', 0x1001, 0x12) + b'\0\xff', select('/etc/passwd'), FILE_WRITE + b'anything'])
def test_forbidden_commands_never_reach_usb(payload):
    backend = Backend()
    guard = Guard(backend, False)
    with pytest.raises(ValueError):
        guard.write(frame(payload))
    assert not backend.writes


def test_default_rejects_font_paths_and_loading(assets):
    backend = Backend()
    guard = Guard(backend, False)
    for path in assets:
        with pytest.raises(ValueError):
            guard.write(frame(select(path)))
    with pytest.raises(ValueError):
        Guard(backend, False, assets)
    assert not backend.writes


def test_exact_multiframe_pdt_one_attempt(backup):
    backend = Backend()
    guard = Guard(backend, False)
    attrs = settings.attributes(backup)
    after = settings.patch(backup, False, 'enable', attrs)
    guard.arm_pdt(backup, after, 'enable', attrs)
    request = WRITE + after
    for offset in range(0, len(request), MAX):
        guard.write(HEADER.pack(len(request)-offset, 0x40, 1, 0, 0, 0, 0) + request[offset:offset+MAX])
    assert len(backend.writes) == 3
    assert b''.join(raw[12:] for raw in backend.writes) == request
    with pytest.raises(ValueError):
        guard.arm_pdt(backup, after, 'enable', attrs)


def test_tampered_continuation_blocked(backup):
    backend = Backend()
    guard = Guard(backend, False)
    attrs = settings.attributes(backup)
    after = settings.patch(backup, False, 'enable', attrs)
    guard.arm_pdt(backup, after, 'enable', attrs)
    request = WRITE + after
    guard.write(frame(request))
    fragment = bytearray(request[MAX:MAX*2])
    fragment[0] ^= 1
    with pytest.raises(ValueError):
        guard.write(HEADER.pack(len(request)-MAX, 0x40, 1, 0, 0, 0, 0) + fragment)
    assert len(backend.writes) == 1


def test_send_failure_poisoned(backup):
    backend = Backend()
    guard = Guard(backend, False)
    backend.fail = True
    with pytest.raises(TimeoutError):
        guard.write(frame(READ))
    backend.fail = False
    with pytest.raises(ValueError):
        guard.write(frame(READ))
    assert len(backend.writes) == 1


def test_bounded_version3_multiframe_reply(backup):
    backend = Backend()
    for offset in range(0, len(backup), MAX):
        backend.reply += HEADER.pack(len(backup)-offset, 0x40, 1, 3, 0, 0, 0) + backup[offset:offset+MAX]
    camera = Camera(Guard(backend, False))
    assert camera.memory() == backup
    assert camera.sequence == 2


def test_wrong_reply_sequence_poisoned():
    backend = Backend()
    backend.reply += HEADER.pack(0, 0x40, 2, 3, 0, 0, 0)
    camera = Camera(Guard(backend, False))
    with pytest.raises(ValueError):
        camera.memory()
    assert camera.guard.poisoned


def test_font_requires_exact_hash_path_and_one_attempt(assets):
    backend = Backend()
    guard = Guard(backend, True, assets)
    path = next(iter(assets))
    guard.write(frame(select(path)))
    guard.arm_font(path)
    with pytest.raises(ValueError):
        guard.write(frame(FILE_WRITE + b'changed'))
    guard.write(frame(FILE_WRITE + assets[path]))
    with pytest.raises(ValueError):
        guard.arm_font(path)


def test_hash_mismatch_rejected(assets):
    assets[next(iter(assets))] = b'changed'
    with pytest.raises(ValueError):
        Guard(Backend(), True, assets)
