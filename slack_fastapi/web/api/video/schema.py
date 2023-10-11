from typing import List, Optional

from pydantic import BaseModel, Field

from slack_fastapi.web.api.generics.schemas import IdSchema, IdStrictSchema


class VideoPropertiesSchema(BaseModel):
    """VideoPropertiesSchema model."""

    duration: int = Field(ge=0)
    video_content_type: str = Field(max_length=200)  # noqa: WPS432
    audio_content_type: str = Field(max_length=200, default=None)  # noqa: WPS432
    frame_width: int = Field(ge=0)
    frame_height: int = Field(ge=0)
    size: int = Field(ge=0)


class VideoSchema(IdSchema):
    """VideoSchema model."""

    video_name: str = Field(max_length=1000)
    properties: Optional[VideoPropertiesSchema]


class ClipSchema(VideoSchema):
    """ClipSchema model."""

    link: str = Field(max_length=1000)


class ClipCreateSchema(IdStrictSchema):
    """ClipCreateSchema model."""

    output_name: str = Field(min_length=5, max_length=20)  # noqa: WPS432


class AllVideosSchema(BaseModel):
    """AllVideosSchema model."""

    videos: Optional[List[VideoSchema]]


class AllClipsSchema(BaseModel):
    """AllClipsSchema model."""

    clips: List[ClipSchema]
