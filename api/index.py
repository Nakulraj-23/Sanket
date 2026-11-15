"""Vercel entry point: the same FastAPI app, with a throw-away SQLite database under /tmp.

Vercel functions are stateless: every cold start builds a fresh database and seeds it with a
smaller set of demo tickets (SANKET_SEED_TICKETS, default 250). Models are read from the
repository's artifacts/ folder, which is read-only there. The neural network is skipped when
onnxruntime is not installed (see sanket.service.load_nn).
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_FILE = Path(tempfile.gettempdir()) / "sanket.db"
os.environ.setdefault("SANKET_DB_URL", f"sqlite:///{DB_FILE}")

from sanket.api.app import create_app
from sanket.config import get_settings
from sanket.service import load_runtime


def _seed_module():
    """Import scripts/seed.py by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("sanket_seed", ROOT / "scripts" / "seed.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_app():
    """Fresh database, load the models once, seed a few tickets, return the app."""
    settings = get_settings()
    seed = _seed_module()
    seed.remove_old_database(settings.db_url)
    runtime = load_runtime(settings)
    seed.main(int(os.environ.get("SANKET_SEED_TICKETS", "250")), rt=runtime)
    application = create_app()
    application.state.runtime = runtime
    return application


app = build_app()
