import ormar

from slack_fastapi.db.base import BaseMeta


class VideoPropertiesModel(ormar.Model):
    """Vide properties model."""

    class Meta(BaseMeta):
        tablename = "video_properties"

    id: int = ormar.Integer(primary_key=True)
    duration: int = ormar.Integer(minimum=0)
    video_content_type: str = ormar.String(max_length=200)  # noqa: WPS432
    audio_content_type: str = ormar.String(
        max_length=200,  # noqa: WPS432
        nullable=True,
    )
    frame_width: int = ormar.Integer(minimum=0)
    frame_height: int = ormar.Integer(minimum=0)
    size: int = ormar.Integer(minimum=0)
