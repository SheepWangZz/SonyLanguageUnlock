"""GUI entry point. --self-test never enumerates or opens USB."""
import argparse
import json
from pathlib import Path
import language_tool


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', metavar='RESULT_JSON')
    args = parser.parse_args()
    if args.self_test:
        from language_tool import settings, fonts
        import libusb_package
        import usb.core
        import usb.backend.libusb1
        from Cryptodome.Cipher import AES
        from pmca.usb.sony import SonySenserAuthDevice
        from fwtool.sony import dat, fdat
        import tkinter as tk
        from language_tool.gui import App
        def no_usb(*args, **kwargs):
            raise AssertionError('Self-test may not enumerate USB')
        usb.core.find = no_usb
        assert len(AES.new(bytes(16), AES.MODE_ECB).encrypt(bytes(16))) == 16
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        root.update_idletasks()
        assert not app.chinese.get()
        assert app.device is None and app.package is None
        assert app.start_button.instate(['disabled'])
        assert app.entry.instate(['disabled']) and app.browse.instate(['disabled'])
        app.device = {'model': 'ILCE-7CM2', 'version': '2.01', 'body_digest': 'offline'}
        app.chinese.set(True)
        app.refresh()
        assert app.browse.instate(['!disabled'])
        app.language.set('English')
        app.refresh()
        assert app.start_button.cget('text') == 'Start unlock'
        assert app.chinese.get() and app.device['version'] == '2.01'
        assert not hasattr(app, 'source_mode')
        app.busy = True
        app.refresh()
        assert app.detect_button.instate(['disabled']) and app.browse.instate(['disabled'])
        app.busy = False
        app.chinese.set(False)
        app.refresh()
        assert app.entry.instate(['disabled']) and app.browse.instate(['disabled'])
        app.language.set('中文')
        app.refresh()
        assert app.start_button.cget('text') == '开始解锁'
        assert settings.desired(False)[settings.CHINESE[0]] == b'\x02'
        assert settings.desired(True)[settings.CHINESE[0]] == b'\x01'
        from language_tool.usb_backend import get_usb_backend, backend_name
        assert get_usb_backend() is not None
        root.destroy()
        Path(args.self_test).write_text(json.dumps({'passed': True, 'usb_enumeration': False,
            'camera_access': False, 'chinese_default': False, 'bundled_fonts': False,
            'firmware_picker': True, 'detection_required': True, 'ui_languages': ['zh', 'en'],
            'usb_backend': backend_name(),
            'font_count': len(fonts.FONTS)}, indent=2), encoding='utf-8')
        return
    from language_tool.gui import main as gui_main
    gui_main()


if __name__ == '__main__':
    main()
