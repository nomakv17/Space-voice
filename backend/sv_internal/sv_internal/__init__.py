"""SpaceVoice Internal Module - Private client analytics."""

from fastapi import FastAPI


def plugin_setup(app: FastAPI) -> None:
    """Register internal module routes and ensure models are loaded."""
    # Import models to register with SQLAlchemy Base (triggers table creation)
    from sv_internal import models

    # Import and register API routers
    from sv_internal.api import clients, income, plugins

    app.include_router(plugins.router)
    app.include_router(clients.router)
    app.include_router(income.router)
