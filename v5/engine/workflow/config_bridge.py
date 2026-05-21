"""Bridge v5 engine to v1/workflow_config package on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_V1_ROOT = _REPO_ROOT / "v1"


def ensure_workflow_config_path() -> Path:
    """Insert v1/ so `import workflow_config` resolves."""
    if str(_V1_ROOT) not in sys.path:
        sys.path.insert(0, str(_V1_ROOT))
    return _V1_ROOT
