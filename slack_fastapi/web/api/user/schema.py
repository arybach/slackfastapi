from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator

from slack_fastapi.settings import settings


class UserClipSettingsSchema(BaseModel):
    """User parameters to change clip settings."""

    trained_model: Optional[str] = Field(default="RanFor_Streams Highlights.joblib")
    max_seconds_lenght: Optional[int] = Field(default="10")  # noqa: WPS432
    model_threshold: Optional[float] = Field(default=-1)  # noqa: WPS432
    median_hit_modificator: Optional[float] = Field(default=3)  # noqa: WPS432
    noice_threshold: Optional[List[int]] = [10, 90]
    audio_threshold: Optional[List[int]] = [25, 75]
    crop_interval: Optional[List[int]] = [1, 5]
    sound_check: Optional[bool] = False

    @root_validator
    def validate_fields(  # noqa: N805, C901, WPS238, WPS231
        cls,  # noqa: N805
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Checks if some values specified in pairs.

        :raises ValueError: Incorrect input
        :param values: Dict
        :return: values
        """
        if not values:
            raise ValueError("No values specified")

        if values.get("trained_model"):
            if values["trained_model"] not in settings.trained_models:
                raise ValueError("No such trained model")

        if values.get("noice_threshold"):
            if len(values["noice_threshold"]) != 2:
                raise ValueError("noice_threshold must consists of 2 int values")
            if values["noice_threshold"][1] <= values["noice_threshold"][0]:
                raise ValueError("First value must be lower then the second one.")

        if values.get("audio_threshold"):
            if len(values["audio_threshold"]) != 2:
                raise ValueError("audio_threshold must consists of 2 int values")
            if values["audio_threshold"][1] <= values["audio_threshold"][0]:
                raise ValueError("First value must be lower then the second one.")

        if values.get("crop_interval"):
            if len(values["crop_interval"]) != 2:
                raise ValueError("crop_interval must consists of 2 int values")
            if values["crop_interval"][1] <= values["crop_interval"][0]:
                raise ValueError("First value must be lower then the second one.")

        return values

    def to_dict_model(self) -> Dict[str, Any]:
        """
        Convert to dict suitable for DB model.

        :return: Dict
        """
        clip_dict = self.dict(exclude_none=True)

        if clip_dict.get("noice_threshold"):
            clip_dict["noice_threshold"] = ",".join(
                map(str, clip_dict["noice_threshold"]),
            )

        if clip_dict.get("audio_threshold"):
            clip_dict["audio_threshold"] = ",".join(
                map(str, clip_dict["audio_threshold"]),
            )

        if clip_dict.get("crop_interval"):
            clip_dict["crop_interval"] = ",".join(map(str, clip_dict["crop_interval"]))

        return clip_dict


class UserSchema(BaseModel):
    """User parameters."""

    id: int
    first_name: str
    last_name: str
    email: str
    role: str
    verified: bool
    created: datetime


class TrainedModelsSchema(BaseModel):
    """List of available models."""

    models: Optional[List[str]]
