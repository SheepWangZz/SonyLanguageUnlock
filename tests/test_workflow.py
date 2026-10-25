from contextlib import contextmanager
import json
import pytest
from language_tool import settings, fonts, workflow
from language_tool.transport import BACKUP, VERSION, FileResultError


class FakeCamera:
    def __init__(self, raw, fail=None):
        self.raw, self.fail = raw, fail
        self.files, self.events = {}, []
        self.assets = None

    def memory(self):
        self.events.append('memory')
        return self.raw

    def read_file(self, path, limit=None):
        self.events.append('read:' + path)
        if path == VERSION:
            return b'\x01\x02'
        if path == BACKUP:
            return self.raw
        if path not in self.files:
            raise FileResultError(0x10000006)
        return self.files[path]

    def write_settings(self, before, candidate, phase, attrs):
        self.events.append(phase)
        if phase == self.fail:
            raise TimeoutError('uncertain write')
        # Emulate the recovered PDT protection rule, independently of patch().
        current, incoming = settings.parse(self.raw), settings.parse(candidate)
        for key in settings.TARGETS:
            new = incoming.getProperty(key)
            if not new.attr & 1:
                current.setProperty(key, new.data)
            current.setPropertyAttr(key, new.attr)
        current.updateChecksum()
        self.raw = current.file.getvalue()

    def write_font(self, path):
        self.events.append('write:' + path)
        if self.fail == path:
            raise TimeoutError('uncertain font write')
        # A font must never be sent before the property locks are restored.
        assert all(a == 1 for a in settings.attributes(self.raw).values())
        self.files[path] = self.assets[path]

    @contextmanager
    def connect(self, chinese, assets, log, state):
        self.assets = assets
        self.events.append('connect:' + str(chinese))
        try:
            yield self
        finally:
            state['normal_usb_return'] = True


def test_default_disables_previously_enabled_chinese_without_any_font_access(tmp_path, backup):
    camera = FakeCamera(backup)
    b = settings.parse(camera.raw)
    for k in settings.CHINESE:
        b.setProperty(k, b'\x01')
    b.updateChecksum()
    camera.raw = b.file.getvalue()
    def forbidden(*args):
        pytest.fail('Chinese source loader called in default mode')
    state = workflow.apply(False, object(), root=tmp_path, connector=camera.connect, loader=forbidden)
    assert state['status'] == 'AWAITING_RESTART'
    settings.verify(camera.raw, False, {k: 1 for k in settings.TARGETS})
    assert not any('/tmp/images/' in e for e in camera.events)
    assert camera.files == {}
    assert camera.events.count('enable') == camera.events.count('restore') == 1
    workflow.verify_after_restart(root=tmp_path, connector=camera.connect, owner_confirmed=True)
    assert not (tmp_path / 'pending.json').exists()
    assert not any('/tmp/images/' in e for e in camera.events)


def test_chinese_order_all_three_resources_and_post_restart_verify(tmp_path, backup, assets):
    camera = FakeCamera(backup)
    state = workflow.apply(True, 'unused', root=tmp_path, connector=camera.connect, loader=lambda *args: assets)
    assert state['three_fonts_verified']
    writes = [e for e in camera.events if e.startswith('write:')]
    assert writes == ['write:' + p for p in assets]
    assert camera.events.index('enable') < camera.events.index('restore') < camera.events.index(writes[0])
    settings.verify(camera.raw, True, {k: 1 for k in settings.TARGETS})
    assert workflow.verify_after_restart(root=tmp_path, connector=camera.connect, owner_confirmed=True)['status'] == 'VERIFIED'


def test_bad_source_stops_before_camera(tmp_path, backup):
    camera = FakeCamera(backup)
    def bad(*args):
        raise ValueError('bad hash')
    with pytest.raises(ValueError, match='bad hash'):
        workflow.apply(True, root=tmp_path, connector=camera.connect, loader=bad)
    assert camera.events == []


def test_existing_different_font_stops_before_settings(tmp_path, backup, assets):
    camera = FakeCamera(backup)
    camera.files[next(iter(assets))] = b'other'
    with pytest.raises(ValueError, match='停止覆盖'):
        workflow.apply(True, root=tmp_path, connector=camera.connect, loader=lambda *args: assets)
    assert 'enable' not in camera.events
    assert not (tmp_path / 'pending.json').exists()


def test_existing_fonts_skipped(tmp_path, backup, assets):
    camera = FakeCamera(backup)
    camera.files.update(assets)
    workflow.apply(True, root=tmp_path, connector=camera.connect, loader=lambda *args: assets)
    assert not any(e.startswith('write:') for e in camera.events)


@pytest.mark.parametrize('failure', ['enable', 'restore', '/tmp/images/MYingHeiC-Big5-SJ_wIcon.ltt'])
def test_uncertain_write_persists_and_blocks_retry(tmp_path, backup, assets, failure):
    camera = FakeCamera(backup, failure)
    with pytest.raises(TimeoutError):
        workflow.apply(True, root=tmp_path, connector=camera.connect, loader=lambda *args: assets)
    assert (tmp_path / 'pending.json').exists()
    before = list(camera.events)
    with pytest.raises(RuntimeError, match='待核对'):
        workflow.apply(True, root=tmp_path, connector=camera.connect, loader=lambda *args: assets)
    assert camera.events == before
    assert camera.events.count(failure if failure in ('enable', 'restore') else 'write:' + failure) == 1


def test_verify_requires_owner_restart_confirmation(tmp_path):
    with pytest.raises(ValueError, match='手动重启'):
        workflow.verify_after_restart(root=tmp_path)


def test_second_body_cannot_clear_pending(tmp_path, backup):
    camera = FakeCamera(backup)
    workflow.apply(False, root=tmp_path, connector=camera.connect)
    b = settings.parse(camera.raw)
    b.setProperty(0xe70003, b'bodytwo!')
    b.updateChecksum()
    camera.raw = b.file.getvalue()
    with pytest.raises(ValueError, match='不是上次'):
        workflow.verify_after_restart(root=tmp_path, connector=camera.connect, owner_confirmed=True)
    assert (tmp_path / 'pending.json').exists()


def test_noop_does_not_write_settings(tmp_path, backup):
    attrs = settings.attributes(backup)
    enabled = settings.patch(backup, False, 'enable', attrs)
    raw = settings.patch(enabled, False, 'restore', attrs)
    camera = FakeCamera(raw)
    workflow.apply(False, root=tmp_path, connector=camera.connect)
    assert 'enable' not in camera.events and 'restore' not in camera.events


def test_partial_unlock_refused(tmp_path, backup):
    b = settings.parse(backup)
    b.setPropertyAttr(settings.TARGETS[0], 0)
    b.updateChecksum()
    camera = FakeCamera(b.file.getvalue())
    with pytest.raises(ValueError, match='保护未恢复'):
        workflow.apply(False, root=tmp_path, connector=camera.connect)
    assert 'enable' not in camera.events
