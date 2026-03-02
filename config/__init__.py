# =====================================================
# CONFIG PACKAGE INITIALIZER (COMPATIBILITY BRIDGE)
# =====================================================
# This package shadows legacy config.py.
# We MUST load config.py explicitly by file path
# and re-export its public symbols.
# =====================================================

import importlib.util
import pathlib
import sys

# ---- locate legacy config.py (one level above this directory) ----
_CONFIG_PY_PATH = pathlib.Path(__file__).resolve().parent.parent / "config.py"

spec = importlib.util.spec_from_file_location("_legacy_config", _CONFIG_PY_PATH)
_legacy_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_legacy_config)

# ---- re-export ALL public names from config.py ----
for _name in dir(_legacy_config):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_legacy_config, _name)

# ---- subscription (new system) ----
from .subscription import (
    DEFAULT_USER_TIER,
    get_tier_config,
    LIVE_REFRESH,
)

# ---- cleanup ----
del importlib, pathlib, sys, spec, _name, _CONFIG_PY_PATH