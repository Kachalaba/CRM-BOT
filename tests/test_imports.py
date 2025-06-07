import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import handlers
import sheets
import main


def test_imports():
    assert handlers.dp is not None
    assert main is not None
    assert sheets is not None
