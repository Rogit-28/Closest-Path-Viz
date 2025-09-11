"""
User settings API routes.
"""

import logging
from fastapi import APIRouter
from app.schemas.pathfinding import UserSettingsSchema

logger = logging.getLogger("pathfinding.api.settings")
router = APIRouter(prefix="/api/user", tags=["settings"])

# In-memory settings store (in production, use database)
_user_settings: dict[str, UserSettingsSchema] = {}

DEFAULT_SETTINGS = UserSettingsSchema()


@router.get("/settings")
async def get_settings(user_id: str = "default"):
    """Get user settings."""
    settings = _user_settings.get(user_id, DEFAULT_SETTINGS)
    return settings.model_dump()


@router.put("/settings")
async def update_settings(settings: UserSettingsSchema, user_id: str = "default"):
    """Update user settings."""
    _user_settings[user_id] = settings
    return settings.model_dump()


@router.delete("/settings")
async def reset_settings(user_id: str = "default"):
    """Reset user settings to defaults."""
    if user_id in _user_settings:
        del _user_settings[user_id]
    return DEFAULT_SETTINGS.model_dump()
