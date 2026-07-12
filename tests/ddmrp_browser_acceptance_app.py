from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from sdbr.api import create_app
from sdbr.ddmrp_replenishment_view import build_ddmrp_replenishment_workbench
from sdbr.state_store import SQLiteWorkbenchStateStore, WorkbenchStateStore


DDMRP_ACCEPTANCE_MODES = frozenset({"seeded", "empty", "error", "403", "409"})
DDMRP_WORKBENCH_ENDPOINT = "/planner/workbench/ddmrp/workbench"


def create_ddmrp_browser_acceptance_app(
    state_store: WorkbenchStateStore,
) -> FastAPI:
    production_app = create_app(state_store=state_store)
    app = FastAPI()
    app.state.ddmrp_acceptance_mode = "seeded"

    @app.put("/__ddmrp_acceptance__/mode/{mode}")
    def set_mode(mode: str) -> dict[str, object]:
        if mode not in DDMRP_ACCEPTANCE_MODES:
            raise HTTPException(
                status_code=422,
                detail="Unsupported DDMRP acceptance mode.",
            )
        app.state.ddmrp_acceptance_mode = mode
        return {"Mode": mode}

    @app.middleware("http")
    async def fixture_mode(request: Request, call_next):
        if (
            request.method != "GET"
            or request.url.path != DDMRP_WORKBENCH_ENDPOINT
        ):
            return await call_next(request)
        mode = str(app.state.ddmrp_acceptance_mode)
        if mode == "seeded":
            return await call_next(request)
        revision = str(state_store.current_revision())
        if mode == "empty":
            data = build_ddmrp_replenishment_workbench(
                evaluation_runs={},
                evaluation_rows={},
                chains={},
                recommendations={},
                events=(),
                active_replenishment_graphs={},
            )
            return JSONResponse(
                status_code=200,
                content={
                    "Endpoint": DDMRP_WORKBENCH_ENDPOINT,
                    "StatusCode": 200,
                    "Data": data,
                },
                headers={"X-Workbench-Revision": revision},
            )
        status_code = {"error": 500, "403": 403, "409": 409}[mode]
        status = {"error": "FixtureError", "403": "Forbidden", "409": "Conflict"}[mode]
        return JSONResponse(
            status_code=status_code,
            content={
                "Endpoint": DDMRP_WORKBENCH_ENDPOINT,
                "StatusCode": status_code,
                "Data": {
                    "Status": status,
                    "Message": f"DDMRP acceptance fixture mode: {mode}",
                },
            },
            headers={"X-Workbench-Revision": revision},
        )

    app.mount("/", production_app)
    return app


def create_runtime_app() -> FastAPI:
    if os.environ.get("SDBR_ENVIRONMENT") != "test":
        raise RuntimeError("SDBR_ENVIRONMENT must be 'test' for browser acceptance.")
    database_path = os.environ.get("SDBR_WORKBENCH_DB_PATH")
    if not database_path:
        raise RuntimeError(
            "SDBR_WORKBENCH_DB_PATH is required for browser acceptance."
        )
    store = SQLiteWorkbenchStateStore(database_path)
    return create_ddmrp_browser_acceptance_app(store)
