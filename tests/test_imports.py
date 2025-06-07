import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import handlers  # noqa: E402
import main  # noqa: E402
import sheets  # noqa: E402


def test_imports():
    assert handlers.dp is not None
    assert main is not None
    assert sheets is not None
