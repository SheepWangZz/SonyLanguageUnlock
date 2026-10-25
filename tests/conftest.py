"""Synthetic BK4 only. No camera backups, serials or Sony fonts in fixtures."""
import hashlib
import io
import struct
import pytest
import language_tool
from pmca.backup import BackupHeader, SubsystemTableEntry, PropertyTableEntryV4, BackupFile
from language_tool import settings, fonts


@pytest.fixture(autouse=True)
def no_usb(monkeypatch):
    import usb.core
    def blocked(*args, **kwargs):
        raise AssertionError('Tests must never enumerate USB')
    monkeypatch.setattr(usb.core, 'find', blocked)


@pytest.fixture
def backup():
    counts = {0xe7: 4, 0x10d: 0xb2}
    ns, np = 0x10e, sum(counts.values())
    offset = BackupHeader.size + ns * SubsystemTableEntry.size + np * PropertyTableEntryV4.size
    table, data, subs, cursor = bytearray(), bytearray(), bytearray(), 0
    for s in range(ns):
        count = counts.get(s, 0)
        subs += SubsystemTableEntry.pack(numProperties=count, ptr=cursor)
        for p in range(count):
            key = (s << 16) | p
            value = (b'fakebody' if key == 0xe70003 else b'Q' if key == 0xe70002 else
                     b'\x02' if key in settings.TARGETS else None)
            ptr = 0xffffffff if value is None else ((len(value) << 24) | (offset + len(data)))
            table += PropertyTableEntryV4.pack(attr=1, ptr=ptr)
            if value:
                data += value
        cursor += count
    header = BackupHeader.pack(magic=0, cookie=0, writeComp=0, revision=b'BK4\0',
        numSubsystems=ns, numProperties=np, dataOffset=offset, dataSize=len(data),
        checksum=0, id1=1, version=b'test', region=b'CX89700_J1')
    raw = bytearray(header + subs + table + data)
    struct.pack_into('<I', raw, 0x20, sum(raw[:0x20] + raw[0x24:]))
    # A large opaque tail exercises multi-frame writes and tail preservation.
    raw += b'TAIL\0' + b'\xa5' * (2 * 1024 * 1024)
    settings.parse(bytes(raw))
    return bytes(raw)


@pytest.fixture
def assets(monkeypatch):
    values = {p: ('synthetic:' + p).encode('ascii') for p in fonts.FONTS}
    monkeypatch.setattr(fonts, 'FONTS', {p: (len(b), hashlib.sha256(b).hexdigest()) for p, b in values.items()})
    return values
