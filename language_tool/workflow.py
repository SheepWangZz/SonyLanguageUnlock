"""Durable one-attempt workflow; no automatic write retries after uncertainty."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
import uuid
from . import settings, fonts
from .transport import connect, BACKUP, VERSION, FileResultError


def state_root():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
    legacy = base / 'A7C2LanguageTool'
    # Retain old pending markers and recovery records across the product rename.
    return legacy if legacy.exists() else base / 'SonyLanguageUnlock'


def write_json(path, value):
    temporary = path.with_suffix('.new')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / 'operation.lock').open('a+b')
    try:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        handle.close()  # OS releases the lock even after process termination.


class Journal:
    def __init__(self, root, chinese):
        self.root = root
        self.folder = root / (time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
        self.folder.mkdir()
        self.state = {'chinese': bool(chinese), 'status': 'PREPARING',
                      'firmware_update_persistence_tested': False,
                      'normal_usb_return': False, 'write_intents': []}
        self.flush()

    def flush(self):
        write_json(self.folder / 'result.json', self.state)

    def snapshot(self, name, raw):
        settings.parse(raw)
        with (self.folder / (name + '.private.bin')).open('wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())

    def intent(self, phase):
        self.state['write_intents'].append(phase)
        self.state['status'] = 'WRITE_IN_PROGRESS'
        self.flush()
        write_json(self.root / 'pending.json', {'session': self.folder.name})


def perform(camera, chinese, assets, journal, log):
    if not chinese and assets:
        raise ValueError('未勾选中文，禁止传入字体资源')
    if chinese:
        fonts.validate(assets)
    if camera.read_file(VERSION, 4096) != b'\x01\x02':
        raise ValueError('相机固件不是已核对的 2.01')
    before = camera.memory()
    attrs = settings.attributes(before)
    if any(value != 1 for value in attrs.values()):
        raise ValueError('发现语言保护未恢复；先核对旧操作记录')
    body = settings.identity(before)
    if journal.state.get('expected_identity') not in (None, body):
        from .i18n import UserError
        raise UserError('device_changed')
    disk = camera.read_file(BACKUP)
    if settings.identity(disk) != body:
        raise ValueError('机身身份读回不一致')
    journal.snapshot('before-memory', before)
    journal.snapshot('before-disk', disk)
    journal.state.update(body_digest=body, original_attrs={str(k): v for k, v in attrs.items()})
    journal.flush()

    if chinese:
        log('核对相机已有中文资源，已有且完全一致的文件会跳过。')
        for path in fonts.FONTS:
            existing_font(camera, path, assets[path])

    # Refresh after resource preflight; never base a merge on a stale disk backup.
    before = camera.memory()
    if settings.identity(before) != body:
        raise ValueError('机身身份改变')
    journal.snapshot('fresh-before-memory', before)
    candidate = settings.patch(before, chinese, 'enable', attrs)
    if candidate != before:
        journal.snapshot('candidate-enable', candidate)
        journal.intent('enable')
        log('正在解除所需属性的保护并设置语言。')
        camera.write_settings(before, candidate, 'enable', attrs)
        after = camera.memory()
        if settings.identity(after) != body:
            raise ValueError('写入后机身身份不一致')
        journal.snapshot('after-enable', after)
        restore = settings.patch(after, chinese, 'restore', attrs)
        journal.snapshot('candidate-restore', restore)
        journal.intent('restore')
        log('正在恢复原有语言保护。')
        camera.write_settings(after, restore, 'restore', attrs)

    for name, raw in [('final-memory', camera.memory()), ('final-disk', camera.read_file(BACKUP))]:
        journal.snapshot(name, raw)
        if settings.identity(raw) != body:
            raise ValueError('机身身份不一致')
        settings.verify(raw, chinese, attrs)
    log('语言设置与保护已读回核对。')

    if chinese:
        for path in fonts.FONTS:
            if existing_font(camera, path, assets[path]):
                log('文件已匹配，跳过：' + path.rsplit('/', 1)[1])
                continue
            journal.intent('font:' + path)
            log('正在补入：' + path.rsplit('/', 1)[1])
            camera.write_font(path)
            if camera.read_file(path) != assets[path]:
                raise ValueError('字体写入后读回不一致；停止，不自动重试')
        journal.state['three_fonts_verified'] = True
        log('两份中文 LTT 与图标 TTF 均已读回核对。')
    else:
        journal.state['font_access'] = False
    journal.state['status'] = 'AWAITING_RESTART'
    journal.flush()
    write_json(journal.root / 'pending.json', {'session': journal.folder.name})


def existing_font(camera, path, expected):
    try:
        actual = camera.read_file(path)
    except FileResultError as exc:
        if exc.result != 0x10000006:
            raise
        # Observed stat failure permits the reviewed one-shot create operation;
        # it does not prove why the camera could not stat that path.
        return False
    if actual != expected:
        raise ValueError('已有资源与官方文件不符，停止覆盖：' + path)
    return True


def apply(chinese=False, source=None, log=lambda message: None, root=None, connector=connect, loader=fonts.load, expected_identity=None):
    root = Path(root) if root is not None else state_root()
    with locked(root):
        if (root / 'pending.json').exists():
            raise RuntimeError('存在待核对操作。请先执行“重启后只读核对”；不要重复写入。记录：' + str(root))
        # The false branch must not inspect even the source path.
        assets = loader(source, log) if chinese else None
        journal = Journal(root, chinese)
        journal.state['expected_identity'] = expected_identity
        try:
            with connector(chinese, assets, log, journal.state) as camera:
                perform(camera, chinese, assets, journal, log)
            if not journal.state['normal_usb_return']:
                raise RuntimeError('写入核对结束，但普通 USB 模式尚未确认恢复；请查看记录后重新连接')
            log('本次读回通过。请断开 USB，关机再开机，检查语言菜单，再连接进行只读核对。')
        except Exception as exc:
            journal.state.update(status='NEEDS_REVIEW', error=str(exc))
            log('已停止：' + str(exc))
            raise
        finally:
            journal.flush()
            log('本机记录：' + str(journal.folder))
        return journal.state


def verify_after_restart(log=lambda message: None, root=None, connector=connect, owner_confirmed=False):
    if not owner_confirmed:
        raise ValueError('请先手动重启并检查语言菜单，再确认只读核对')
    root = Path(root) if root is not None else state_root()
    with locked(root):
        pending = root / 'pending.json'
        if not pending.exists():
            raise ValueError('没有待核对的操作记录')
        name = json.loads(pending.read_text(encoding='utf-8'))['session']
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('操作记录路径无效')
        folder = root / name
        state = json.loads((folder / 'result.json').read_text(encoding='utf-8'))
        chinese = state['chinese']
        attrs = {int(k): v for k, v in state['original_attrs'].items()}
        connection_state = {}
        try:
            with connector(chinese, None, log, connection_state) as camera:
                if camera.read_file(VERSION, 4096) != b'\x01\x02':
                    raise ValueError('相机固件版本改变，不能套用旧结论')
                for raw in (camera.memory(), camera.read_file(BACKUP)):
                    if settings.identity(raw) != state['body_digest']:
                        raise ValueError('连接的相机不是上次操作的机身')
                    settings.verify(raw, chinese, attrs)
                if chinese:
                    for path in fonts.FONTS:
                        if not fonts.matches(path, camera.read_file(path)):
                            raise ValueError('重启后字体核对失败：' + path)
            if not connection_state.get('normal_usb_return'):
                raise RuntimeError('普通 USB 模式尚未确认恢复')
            state.update(status='VERIFIED', owner_reported_restart_and_menu_ok=True,
                         post_restart_readback=True, verification_connection=connection_state)
            write_json(folder / 'result.json', state)
            pending.unlink()
            log('只读核对通过；重启与菜单正常由你确认，语言及保护状态已读回验证。')
            return state
        except Exception as exc:
            state['last_verify_error'] = str(exc)
            write_json(folder / 'result.json', state)
            raise
