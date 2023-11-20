from importlib import metadata
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import UJSONResponse

from slack_fastapi.logger.services import LoggerMiddleware
from slack_fastapi.logging import configure_logging
from slack_fastapi.settings import settings
from slack_fastapi.web.api.dummy.views import (
    router as dummy_router,  # Import dummy router for tests
)
from slack_fastapi.web.api.echo.views import (
    router as echo_router,  # Import echo router for tests
)
from slack_fastapi.web.api.router import api_router
from slack_fastapi.web.lifetime import register_shutdown_event, register_startup_event

middleware = LoggerMiddleware()


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    configure_logging()
    app = FastAPI(
        title=settings.docs_title,
        description=settings.docs_description,
        version=metadata.version("slack_fastapi"),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
    )

    # Settings CORS middleware.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Adds startup and shutdown events.
    register_startup_event(app)
    register_shutdown_event(app)

    # Main router for the API.
    app.include_router(router=api_router, prefix="/api")

    # Include the dummy router with a specific path prefix for tests
    app.include_router(dummy_router, prefix="/dummy", tags=["dummy"])

    # Include the echo router with a specific path prefix for tests
    app.include_router(echo_router, prefix="/echo", tags=["echo"])

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any):  # type: ignore # noqa: WPS430, E501
        return await middleware.process_request(request=request, call_next=call_next)

    return app
