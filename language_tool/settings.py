"""Pure, byte-scoped BK4 transformations; preserve the concatenated tail."""
import hashlib
import io
from pmca.backup import BackupFile

TARGETS = tuple(range(0x010d008f, 0x010d008f + 35))
CHINESE = (0x010d0096, 0x010d0097)
LIMIT = 4 * 1024 * 1024


def parse(raw):
    if not 256 < len(raw) <= LIMIT:
        raise ValueError('Backup 大小超出已核对范围')
    b = BackupFile(io.BytesIO(raw))
    if b.revision != 4 or not 256 <= b.size <= len(raw):
        raise ValueError('不支持的 Backup 格式')
    if b.getRegion() != 'CX89700_J1' or b.getId1() != 1:
        raise ValueError('仅支持已核对的日版 J1 / ID1=1 配置')
    for key in TARGETS:
        p = b.getProperty(key)
        if p.data not in (b'\x01', b'\x02') or p.attr not in (0, 1) or p.resetData is not None:
            raise ValueError('语言属性布局不符合已核对版本')
    return b


def identity(raw):
    data = parse(raw).getProperty(0x00e70003).data
    if not data or not any(data):
        raise ValueError('无法读取机身身份')
    return hashlib.sha256(data).hexdigest()


def desired(chinese):
    return {k: b'\x02' if k in CHINESE and not chinese else b'\x01' for k in TARGETS}


def attributes(raw):
    b = parse(raw)
    return {k: b.getProperty(k).attr for k in TARGETS}


def patch(raw, chinese, phase, original_attrs):
    b = parse(raw)
    if set(original_attrs) != set(TARGETS) or any(a != 1 for a in original_attrs.values()):
        raise ValueError('初始语言保护属性必须全部为 1；异常状态需先核对')
    if phase not in ('enable', 'restore'):
        raise ValueError('未知阶段')
    for key, value in desired(chinese).items():
        p = b.getProperty(key)
        if phase == 'enable':
            if p.attr != original_attrs[key]:
                raise ValueError('初始保护属性发生变化')
            if p.data != value:
                b.setPropertyAttr(key, p.attr & ~1)
                b.setProperty(key, value)
        else:
            if p.data != value:
                raise ValueError('语言设置读回不一致；停止后续写入')
            b.setPropertyAttr(key, original_attrs[key])
    b.updateChecksum()
    result = b.file.getvalue()
    validate_candidate(raw, result, chinese, phase, original_attrs)
    return result


def validate_candidate(before, after, chinese, phase, original_attrs):
    a, b = parse(before), parse(after)
    if len(before) != len(after) or a.size != b.size:
        raise ValueError('Backup 长度发生变化')
    allowed = set(range(0x20, 0x24))
    for key, value in desired(chinese).items():
        p, q = a.getProperty(key), b.getProperty(key)
        if phase == 'enable':
            expected_attr = p.attr & ~1 if p.data != value else p.attr
            if p.attr != original_attrs[key] or q.data != value or q.attr != expected_attr:
                raise ValueError('语言解锁候选校验失败')
        elif phase == 'restore':
            if p.data != value or q.data != p.data or q.attr != original_attrs[key]:
                raise ValueError('保护恢复候选校验失败')
        else:
            raise ValueError('未知阶段')
        offset = a._getPropertyTableOffset(key)
        allowed.update((offset, offset + 1, a._readProperty(key).ptr))
    if any(x != y and i not in allowed for i, (x, y) in enumerate(zip(before, after))):
        raise ValueError('候选修改了目标范围以外的字节')


def verify(raw, chinese, original_attrs):
    b = parse(raw)
    for key, value in desired(chinese).items():
        p = b.getProperty(key)
        if p.data != value or p.attr != original_attrs[key]:
            raise ValueError(f'语言或保护读回不一致：{key:08x}')
