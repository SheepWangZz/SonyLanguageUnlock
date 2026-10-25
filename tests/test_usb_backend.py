from types import SimpleNamespace
import pytest
from language_tool import usb_backend
from language_tool.i18n import UserError


def test_windows_uses_bundled_libusb1(monkeypatch):
    import usb.backend.libusb1
    import libusb_package
    backend = object()
    loaders = []
    monkeypatch.setattr(usb_backend, 'os', SimpleNamespace(name='nt'))
    def load(**kwargs):
        loaders.append(kwargs['find_library'])
        return backend
    monkeypatch.setattr(usb.backend.libusb1, 'get_backend', load)
    assert usb_backend.get_usb_backend() is backend
    assert loaders == [libusb_package.find_library]
    assert usb_backend.backend_name() == 'libusb1 / WinUSB'


def test_missing_bundled_library_has_actionable_error(monkeypatch):
    import usb.backend.libusb1
    monkeypatch.setattr(usb.backend.libusb1, 'get_backend', lambda **kw: None)
    with pytest.raises(UserError) as error:
        usb_backend.get_usb_backend()
    assert error.value.key == 'libusb1_missing'


@pytest.mark.parametrize('present', [False, True])
def test_service_enumerates_only_target_with_same_backend(monkeypatch, present):
    import usb.core
    primary, device = object(), object()
    calls = []
    def find(**kwargs):
        calls.append(kwargs)
        return [device] if present else []
    monkeypatch.setattr(usb_backend, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(usb.core, 'find', find)
    devices, name = usb_backend.find_service_devices(primary)
    assert devices == ([device] if present else [])
    assert name == 'libusb1 / WinUSB'
    assert calls == [dict(find_all=True, idVendor=0x054c, idProduct=0x0336, backend=primary)]
