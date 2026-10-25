"""SonyLanguageUnlock. Importing never accesses USB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
__version__ = '0.3.2'
