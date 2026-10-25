from pathlib import Path
from PyInstaller.utils.hooks import collect_all

base = Path(SPECPATH)
usb_data, usb_binaries, usb_hidden = collect_all('libusb_package')
usb_hidden = [name for name in usb_hidden if '.__pyinstaller' not in name]
a = Analysis([str(base / 'app.py')], pathex=[str(base), str(base / 'language_tool/vendor')],
    binaries=usb_binaries, datas=usb_data,
    hiddenimports=usb_hidden, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['pytest', 'setuptools', 'pip'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SonyLanguageUnlock',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SonyLanguageUnlock')
