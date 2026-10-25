"""Explicit offline validation against owner-supplied files. Never opens USB."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_tool import settings, fonts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    import usb.core
    def no_usb(*args, **kwargs):
        raise AssertionError('Offline validation may not enumerate USB')
    usb.core.find = no_usb
    raw = args.backup.read_bytes()
    attrs = settings.attributes(raw)
    modes = {}
    for chinese in (False, True):
        first = settings.patch(raw, chinese, 'enable', attrs)
        final = settings.patch(first, chinese, 'restore', attrs)
        settings.verify(final, chinese, attrs)
        # Independent recovered merge-rule check: incoming attr bit 0 blocks data.
        merged = settings.parse(raw)
        for candidate in (first, final):
            incoming = settings.parse(candidate)
            for key in settings.TARGETS:
                p = incoming.getProperty(key)
                if not p.attr & 1:
                    merged.setProperty(key, p.data)
                merged.setPropertyAttr(key, p.attr)
            merged.updateChecksum()
        settings.verify(merged.file.getvalue(), chinese, attrs)
        modes[str(chinese)] = {'verified': True, 'tail_preserved': final[settings.parse(raw).size:] == raw[settings.parse(raw).size:],
                              'changed_bytes': sum(x != y for x, y in zip(raw, final))}
    assets = fonts.load(args.source, print)
    result = {'passed': True, 'camera_access': False, 'modes': modes,
              'assets': {p: {'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for p, b in assets.items()},
              'not_proven': ['new_GUI_live_workflow', 'firmware_update_persistence']}
    args.result.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
