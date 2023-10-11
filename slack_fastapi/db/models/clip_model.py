import ormar

from slack_fastapi.db.base import BaseMeta
from slack_fastapi.db.models.user_model import UserModel
from slack_fastapi.db.models.video_properties_model import VideoPropertiesModel


class ClipModel(ormar.Model):
    """Clip model."""

    class Meta(BaseMeta):
        tablename = "clips"

    id: int = ormar.Integer(primary_key=True)
    user: UserModel = ormar.ForeignKey(UserModel)
    video_properties: VideoPropertiesModel = ormar.ForeignKey(VideoPropertiesModel)
    name: str = ormar.String(max_length=200)  # noqa: WPS432
    video_key: str = ormar.String(max_length=1000)
