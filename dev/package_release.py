"""Package explicit deliverables; exclude local evidence and build environments."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from language_tool import __version__
dist = root / 'dist'
app = dist / 'SonyLanguageUnlock'
for name in ('README.md', 'README.en.md', 'GITHUB_UPLOAD.md', 'THIRD_PARTY.md', 'VALIDATION.md', 'FONT_COMPARISON.md', 'SPONSOR.md'):
    shutil.copyfile(root / name, app / name)

sponsor_assets = app / 'assets' / 'sponsor'
sponsor_assets.mkdir(parents=True, exist_ok=True)
for name in ('wechat.jpg', 'alipay.jpg', 'usdt-bsc.png'):
    shutil.copyfile(root / 'assets' / 'sponsor' / name, sponsor_assets / name)


def check_name(path, original):
    assert not any(part in {'.build', 'build', '__pycache__', '.pytest_cache'} for part in path.parts)
    assert '.private.' not in path.name
    assert path.suffix.lower() not in {'.dat', '.ltt', '.ttf'}
    assert '.git' not in path.parts and path.name != '.env'


runtime = dist / f'SonyLanguageUnlock-{__version__}-windows-x64.zip'
with zipfile.ZipFile(runtime, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(app.rglob('*')):
        if path.is_file():
            relative = path.relative_to(dist)
            check_name(relative, path)
            archive.write(path, relative)

source = dist / f'SonyLanguageUnlock-{__version__}-source.zip'
excluded = {'.build', 'build', 'dist', '__pycache__', '.pytest_cache', '.git', '.venv'}
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if path.is_file() and not any(part in excluded for part in relative.parts):
            if path.suffix.lower() in {'.dat', '.ltt', '.ttf'} or path.name == '.env':
                continue
            check_name(relative, path)
            archive.write(path, Path('SonyLanguageUnlock') / relative)

checks = {}
for path in (runtime, source):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert not any(Path(name).suffix.lower() in {'.dat', '.ltt', '.ttf'} for name in names)
    checks[path.name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'entries': len(names)}
(dist / 'release-checksums.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
print(json.dumps(checks, indent=2))
