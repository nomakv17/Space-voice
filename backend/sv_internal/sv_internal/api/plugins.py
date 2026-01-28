"""Plugin navigation endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


@router.get("/nav")
async def get_plugin_nav() -> list[dict[str, str]]:
    """Return navigation items for installed plugins.

    This endpoint is called by the frontend sidebar to dynamically load
    nav items from installed plugins. Returns an empty list when no
    plugins are installed.
    """
    return [
        {
            "name": "Income",
            "href": "/dashboard/income",
            "icon": "DollarSign",
            "color": "text-emerald-400",
        }
    ]
