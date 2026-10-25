"""Use bundled libusb1 with WinUSB for both Windows camera interfaces."""
import os
from .i18n import UserError


def get_usb_backend():
    import usb.backend.libusb1
    import libusb_package
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    if backend is None:
        raise UserError('libusb1_missing')
    return backend


def backend_name():
    return 'libusb1 / WinUSB' if os.name == 'nt' else 'libusb1'


def find_service_devices(primary):
    """Enumerate the service ID with the same backend; no backend fallback."""
    import usb.core
    devices = list(usb.core.find(find_all=True, idVendor=0x054c,
                                idProduct=0x0336, backend=primary))
    return devices, backend_name()
