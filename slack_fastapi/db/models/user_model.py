from datetime import datetime

import ormar

from slack_fastapi.db.base import BaseMeta


class UserClipSettingsModel(ormar.Model):
    """User clip settings model."""

    class Meta(BaseMeta):
        tablename = "user_clip_settings"

    id: int = ormar.Integer(primary_key=True)
    trained_model: str = ormar.String(max_length=200, nullable=True)  # noqa: WPS432
    max_seconds_lenght: int = ormar.Integer(minimum=0, nullable=True)
    model_threshold: float = ormar.Float(minimum=-1, nullable=True)
    median_hit_modificator: float = ormar.Float(minimum=0, nullable=True)
    noice_threshold: str = ormar.String(max_length=200, nullable=True)  # noqa: WPS432
    audio_threshold: str = ormar.String(max_length=200, nullable=True)  # noqa: WPS432
    sound_check: bool = ormar.Boolean(default=True)
    crop_interval: str = ormar.String(max_length=200, nullable=True)  # noqa: WPS432


class UserModel(ormar.Model):
    """User model."""

    class Meta(BaseMeta):
        tablename = "users"

    id: int = ormar.Integer(primary_key=True)
    first_name: str = ormar.String(max_length=50, nullable=True)
    last_name: str = ormar.String(max_length=50, nullable=True)
    email: str = ormar.String(max_length=100, unique=True)
    password: str = ormar.String(max_length=60, nullable=True)
    role: str = ormar.String(
        max_length=20,  # noqa: WPS432
        default="basic",
        regex="^basic$|^premium$|^admin$",
    )
    code: str = ormar.String(max_length=4, nullable=True)
    verified: bool = ormar.Boolean(default=False)
    set_up: bool = ormar.Boolean(default=False)
    clip_settings: UserClipSettingsModel = ormar.ForeignKey(UserClipSettingsModel)
    created: datetime = ormar.DateTime(default=datetime.now())
