"""Offline package identification. File names are never treated as version evidence."""
import hashlib
from pathlib import Path
import tempfile
from .i18n import UserError

MODEL = 'ILCE-7CM2'
MODEL_CODE = 0x20030014
KNOWN = {
    '53bf899210cdc9d83574c114bb5771c31c6166fbbabd878f966c30db0af2e7cf': ('1.01', 1041261016),
    '9e53d7f7914b1518b842836e800221f64c139116a47ced53c18d842ca7106913': ('1.02', 1042188760),
    'b7f8a98c11c51c939bf08611cfa461c1ec698c689f8fae05321e97bcbf1b59f8': ('2.00', 1139212760),
    'eb4943e6099754d64deaef5047942e9bfe258f232d0b7bc39fa23b3cd10e1e31': ('2.01', 1139929560),
}
MAX_PACKAGE = 2 * 1024 * 1024 * 1024


def inspect_package(path):
    path = Path(path)
    if not path.is_file() or not 32 < path.stat().st_size <= MAX_PACKAGE:
        raise UserError('invalid_package')
    with path.open('rb') as stream:
        size = path.stat().st_size
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest in KNOWN:
            version, expected_size = KNOWN[digest]
            if size != expected_size:
                raise UserError('invalid_package')
            code = MODEL_CODE
        else:
            # Identify an unreviewed package for an accurate mismatch message,
            # but do not authorize its assets for writing.
            from fwtool.sony import dat, fdat
            stream.seek(0)
            try:
                outer = dat.readDat(stream)
                _, plain = fdat.decryptFdat(outer.firmwareData)
                with tempfile.TemporaryFile() as decoded:
                    total = 0
                    while chunk := plain.read(1024 * 1024):
                        total += len(chunk)
                        if total > MAX_PACKAGE:
                            raise UserError('invalid_package')
                        decoded.write(chunk)
                    decoded.seek(0)
                    contents = fdat.readFdat(decoded)
                    code, version = contents.model, contents.version
            except Exception as exc:
                raise UserError('invalid_package') from exc
    return {'path': str(path.resolve()), 'sha256': digest, 'size': size,
            'model_code': code, 'model': MODEL if code == MODEL_CODE else f'0x{code:08x}',
            'version': version, 'reviewed': digest in KNOWN}


def check_selection(device, chinese, package):
    if device is None:
        raise UserError('detect_first')
    if not chinese:
        return
    if package is None:
        raise UserError('select_required')
    if package['model'].startswith('0x'):
        # An unmapped model code is unknown, not proof of a different model.
        raise UserError('package_unverified')
    if package['model'] != device['model']:
        raise UserError('model_mismatch', device=device['model'], package=package['model'])
    if package['version'] != device['version']:
        raise UserError('version_mismatch', device=device['version'], package=package['version'])
    if not package['reviewed']:
        raise UserError('package_unverified')


def require_supported(device):
    if device['model'] != MODEL or device['version'] != '2.01':
        raise UserError('unsupported', model=device['model'], version=device['version'])
