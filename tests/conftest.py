"""Pytest configuration and environment fixtures for Hello Farmer."""
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Support container execution where app resides in /app/app
if Path("/app/app").exists():
    import types
    if "backend" not in sys.modules:
        try:
            import app
            backend_mod = types.ModuleType("backend")
            backend_mod.app = app
            sys.modules["backend"] = backend_mod
            sys.modules["backend.app"] = app
        except ImportError:
            pass
