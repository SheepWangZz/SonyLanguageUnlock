"""Copy notices from the actual build environment, not from a web template."""
import importlib.metadata
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
for name in ('pyusb', 'libusb-package', 'pycryptodomex', 'pyinstaller', 'importlib_resources', 'cffi', 'pycparser'):
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        if name not in ('cffi', 'pycparser'):
            raise
        continue  # Optional crypto backend; ctypes works without these packages.
    copied = []
    for item in dist.files or []:
        if item.name.lower().startswith(('license', 'copying')):
            source = Path(dist.locate_file(item))
            if source.is_file():
                destination = root / 'licenses' / name / str(item).replace('/', '__').replace('\\', '__')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                copied.append(destination.name)
    print(name, copied)
for folder in (Path(sys.base_prefix), Path(sys.base_prefix) / 'tcl'):
    if folder.exists():
        for source in folder.glob('**/license.terms') if folder.name == 'tcl' else folder.glob('LICENSE*'):
            destination = root / 'licenses' / 'python-tcl-tk' / (source.parent.name + '-' + source.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
