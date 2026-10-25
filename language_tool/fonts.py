"""Read three exact assets only when Chinese is explicitly selected."""
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile

FONTS = {
    '/tmp/images/MYingHeiC-GB18030-SJ_wIcon.ltt': (2054740, 'a8afccc2e226d5a519f3698796c2a76a0ad6e163f7e5fc9e35d5e89d58db3276'),
    '/tmp/images/MYingHeiC-Big5-SJ_wIcon.ltt': (1150740, '25f3afa8008c6d038e5bf61582c06539a70786a2de1c74fe63e73814d468ab9f'),
    '/tmp/images/Sony_DI_Icons.ttf': (622344, 'f4957fda675cad6c118c91297ed53828fbe4ef0ea28bc50ae2db3458bc5341c2'),
}
DAT_SIZE = 1139929560
DAT_SHA = 'eb4943e6099754d64deaef5047942e9bfe258f232d0b7bc39fa23b3cd10e1e31'


def matches(path, data):
    return (len(data), hashlib.sha256(data).hexdigest()) == FONTS[path]


def validate(assets):
    if set(assets) != set(FONTS) or any(not matches(p, data) for p, data in assets.items()):
        raise ValueError('中文资源大小或 SHA-256 与官方 2.01 不符')
    return assets


def load(source=None, log=lambda message: None):
    if source is None or source == '':
        from .i18n import UserError
        raise UserError('select_required')
    source = Path(source)
    if not source.is_file() or source.stat().st_size != DAT_SIZE:
        raise ValueError('请选择官方 ILCE-7CM2 2.01 BODYDATA.DAT')
    log('正在核对官方 2.01 固件包；此时尚未连接相机。')
    with source.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != DAT_SHA:
            raise ValueError('固件包 SHA-256 不符合已核对的官方 2.01')
        stream.seek(0)
        from fwtool.sony import dat, fdat
        outer = dat.readDat(stream)
        _, plain = fdat.decryptFdat(outer.firmwareData)
        log('正在离线提取两份中文 LTT 与共享图标 TTF，可能需要几分钟。')
        with tempfile.TemporaryFile() as decoded:
            shutil.copyfileobj(plain, decoded, 1024 * 1024)
            decoded.seek(0)
            contents = fdat.readFdat(decoded)
            if contents.model != 0x20030014 or contents.version != '2.01':
                raise ValueError('固件型号或版本不匹配')
            names = {'0800_appli' + p: p for p in FONTS}
            assets = {}
            with tarfile.open(fileobj=contents.firmware, mode='r:') as archive:
                for member in archive:
                    name = member.name.removeprefix('./')
                    if name not in names:
                        continue
                    path = names[name]
                    if path in assets or not member.isfile() or member.size != FONTS[path][0]:
                        raise ValueError('固件内资源条目不符合预期')
                    with archive.extractfile(member) as handle:
                        assets[path] = handle.read(member.size + 1)
            return validate(assets)
