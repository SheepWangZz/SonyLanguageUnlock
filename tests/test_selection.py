import hashlib
import pytest
from language_tool import controller, firmware, fonts, workflow
from language_tool.i18n import TEXT, UserError, translate
from test_workflow import FakeCamera

DEVICE = {'model': 'ILCE-7CM2', 'version': '2.01', 'body_digest': 'test'}
PACKAGE = {'model': 'ILCE-7CM2', 'version': '2.01', 'path': 'BODYDATA.DAT',
           'sha256': fonts.DAT_SHA, 'reviewed': True}


def test_detection_required():
    with pytest.raises(UserError, match='检测'):
        firmware.check_selection(None, False, None)


def test_chinese_requires_firmware_without_bundled_fallback(tmp_path):
    with pytest.raises(UserError) as error:
        workflow.apply(True, root=tmp_path, connector=lambda *args: pytest.fail('Connected'))
    assert error.value.key == 'select_required'


@pytest.mark.parametrize('changes,key', [({'version': '2.00'}, 'version_mismatch'),
    ({'model': 'OTHER'}, 'model_mismatch'), ({'model': '0x12345678'}, 'package_unverified'),
    ({'reviewed': False}, 'package_unverified')])
def test_package_mismatch_is_specific(changes, key):
    with pytest.raises(UserError) as error:
        firmware.check_selection(DEVICE, True, dict(PACKAGE, **changes))
    assert error.value.key == key


def test_non_chinese_ignores_package_entirely():
    calls = []
    controller.execute(DEVICE, False, object(), detector=lambda: dict(DEVICE),
                       apply=lambda *args, **kw: calls.append((args, kw)))
    assert calls[0][1]['source'] is None
    assert calls[0][1]['expected_identity'] == 'test'


@pytest.mark.parametrize('changes', [{'model': 'OTHER'}, {'version': '2.00'}, {'body_digest': 'another'}])
def test_camera_changed_before_unlock_stops(changes):
    with pytest.raises(UserError) as error:
        controller.execute(DEVICE, True, PACKAGE, detector=lambda: dict(DEVICE, **changes),
                           apply=lambda *a, **kw: pytest.fail('Write started'))
    assert error.value.key == 'device_changed'


def test_chinese_passes_selected_package_and_identity():
    calls = []
    controller.execute(DEVICE, True, PACKAGE, detector=lambda: dict(DEVICE),
                       apply=lambda *a, **kw: calls.append((a, kw)))
    assert calls[0][0] == (True,)
    assert calls[0][1]['source'] == PACKAGE['path']


def test_service_body_must_match_detection(tmp_path, backup):
    camera = FakeCamera(backup)
    with pytest.raises(UserError) as error:
        workflow.apply(False, root=tmp_path, connector=camera.connect, expected_identity='other')
    assert error.value.key == 'device_changed'
    assert 'enable' not in camera.events


def test_old_pending_records_survive_rename(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert workflow.state_root().name == 'SonyLanguageUnlock'
    legacy = tmp_path / 'A7C2LanguageTool'
    legacy.mkdir()
    (legacy / 'pending.json').write_text('{}')
    assert workflow.state_root() == legacy


def test_package_version_comes_from_content_not_filename(tmp_path, monkeypatch):
    data = b'known firmware test fixture' * 4
    path = tmp_path / 'pretend-version-9.99.DAT'
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setitem(firmware.KNOWN, digest, ('2.00', len(data)))
    result = firmware.inspect_package(path)
    assert result['version'] == '2.00'
    with pytest.raises(UserError, match='版本不一致'):
        firmware.check_selection(DEVICE, True, result)


def test_invalid_package_rejected(tmp_path):
    path = tmp_path / 'BODYDATA.DAT'
    path.write_bytes(b'not a firmware' * 5)
    with pytest.raises(UserError) as error:
        firmware.inspect_package(path)
    assert error.value.key == 'invalid_package'


def test_both_languages_have_matching_placeholders():
    import string
    for key, pair in TEXT.items():
        assert len(pair) == 2 and all(pair)
        variables = [{field for _, field, _, _ in string.Formatter().parse(text) if field} for text in pair]
        assert variables[0] == variables[1], key
    assert 'Firmware version mismatch' in translate('version_mismatch', 'en', device='2.01', package='2.00')


def test_unvalidated_model_cannot_start():
    with pytest.raises(UserError) as error:
        controller.execute(dict(DEVICE, model='ILCE-7M4'), False, None,
                           detector=lambda: pytest.fail('Unexpected query'))
    assert error.value.key == 'unsupported'
