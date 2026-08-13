"""FastAPI application assembly — router wiring, error-handling middleware,
health check. Per plan.md ("app.py # FastAPI app assembly / DI wiring").

DI wiring in this codebase is FastAPI's own `Depends(...)` mechanism (see
`shared_kernel.infrastructure.db.get_db_session`,
`identity.api.dependencies.get_current_user_id`) — there is no separate
container/registry. AI-provider selection (which concrete `AgentPort`
adapter backs each agent) is handled by `ai_agents.adapter_factory.
get_agent_adapter()` (T068), driven by the `AI_PROVIDER` env var
(`local`/`anthropic`/`openai`) — application services call that factory
instead of instantiating a concrete adapter directly. `NullAudioAdapter`
is still constructed directly where used (T069) since only one
implementation of the audio ports exists this iteration.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from conversation.api.routes import router as conversation_router
from gamification.api.routes import router as gamification_router
from identity.api.routes import router as identity_router
from learning_content.api.routes import router as learning_content_router
from placement.api.routes import router as placement_router
from progression.api.routes import router as progression_router

app = FastAPI(title="LingoAI API", version="0.1.0")

app.include_router(identity_router)
app.include_router(placement_router)
app.include_router(progression_router)
app.include_router(conversation_router)
app.include_router(learning_content_router)
app.include_router(gamification_router)

# Cross-cutting error shape per contracts/rest-api.md:
# {"error": {"code": string, "message": string}} — no endpoint's error
# response should ever look different from this.
_STATUS_CODE_SLUGS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
}


def _status_code_slug(status_code: int) -> str:
    return _STATUS_CODE_SLUGS.get(status_code, f"http_{status_code}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _status_code_slug(exc.status_code),
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": exc.errors()}},
    )


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
