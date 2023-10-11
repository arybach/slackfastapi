import datetime

import ormar

from slack_fastapi.db.base import BaseMeta
from slack_fastapi.db.models.user_model import UserModel
from slack_fastapi.db.models.video_properties_model import VideoPropertiesModel


class VideoModel(ormar.Model):
    """Video model."""

    class Meta(BaseMeta):
        tablename = "videos"

    id: int = ormar.Integer(primary_key=True)
    user: UserModel = ormar.ForeignKey(UserModel)
    uploaded: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    video_properties: VideoPropertiesModel = ormar.ForeignKey(VideoPropertiesModel)
    name: str = ormar.String(max_length=200)  # noqa: WPS432
    video_key: str = ormar.String(max_length=1000)
    audio_key: str = ormar.String(max_length=1000, nullable=True)
