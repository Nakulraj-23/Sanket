"""FastAPI app: CORS, request-size limit, error shapes and the two routers."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sanket.api import ops, tickets
from sanket.config import get_settings
from sanket.service import load_runtime

MAX_BODY_BYTES = 20_000  # a 2,000-character ticket is far below this even with escapes


def create_app() -> FastAPI:
    """Build the app. The models load once at start-up and live on app.state.runtime."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # A host such as Vercel may attach a ready runtime before start-up; keep it.
        if getattr(app.state, "runtime", None) is None:
            app.state.runtime = load_runtime()
        yield

    settings = get_settings()
    app = FastAPI(title="SANKET", version="0.1.0", lifespan=lifespan)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"],
                       allow_headers=["*"])

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        """Refuse bodies over 20 kB before reading them."""
        size = request.headers.get("content-length")
        if size and size.isdigit() and int(size) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        """Errors are always {"detail": "<one string>"}."""
        parts = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        return JSONResponse({"detail": "; ".join(parts)}, status_code=422)

    app.include_router(tickets.router, prefix="/api")
    app.include_router(ops.router, prefix="/api")
    return app


app = create_app()
