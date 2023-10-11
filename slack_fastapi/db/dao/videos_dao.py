from datetime import datetime
from typing import Any, Dict, List

import ormar
from ormar.exceptions import NoMatch

from slack_fastapi.db.models.clip_model import ClipModel
from slack_fastapi.db.models.video_model import VideoModel
from slack_fastapi.db.models.video_properties_model import VideoPropertiesModel
from slack_fastapi.web.api.video.schema import VideoPropertiesSchema


class VideoDAO:
    """Class for accessing video related tables."""

    @staticmethod
    async def create_video_model(
        video_dict: Dict[str, Any],
        properties_object: VideoPropertiesSchema,
    ) -> VideoModel:
        """
        Creates VideoModel entry in DB.

        :param video_dict: VieoModel dict
        :param properties_object: VideoPropertiesSchema
        :return: VideoModel
        """
        video_properties = await VideoPropertiesModel(
            duration=properties_object.duration,
            video_content_type=properties_object.video_content_type,
            audio_content_type=properties_object.audio_content_type,
            frame_width=properties_object.frame_width,
            frame_height=properties_object.frame_height,
            size=properties_object.size,
        ).save()

        return await VideoModel.objects.create(
            video_properties=video_properties,
            **video_dict,
        )

    @staticmethod
    async def create_clip_model(
        clip_dict: Dict[str, Any],
        properties_object: VideoPropertiesSchema,
    ) -> ClipModel:
        """
        Creates ClipModel entry in DB.

        :param clip_dict: ClipModel dict
        :param properties_object: VideoPropertiesSchema
        :return: ClipModel
        """
        video_properties = await VideoPropertiesModel(
            duration=properties_object.duration,
            video_content_type=properties_object.video_content_type,
            frame_width=properties_object.frame_width,
            frame_height=properties_object.frame_height,
            size=properties_object.size,
        ).save()

        return await ClipModel.objects.create(
            video_properties=video_properties,
            **clip_dict,
        )

    @staticmethod
    async def get_audio_key_links(
        user_id: int,
        audio_key: str,
    ) -> int:
        """
        Returns number of VideoModels with the same audio_key.

        :param user_id: User's id
        :param audio_key: Audio Key
        :return: number of VideoModels with the same audio_key.
        """
        return await VideoModel.objects.filter(
            ormar.and_(
                user=user_id,
                audio_key=audio_key,
            ),
        ).count()

    @staticmethod
    async def get_video(
        video_id: int,
        user_id: int,
    ) -> VideoModel | None:
        """
        Returns VideoModel with specified video_id and user_id.

        :param video_id: VideoModel's id
        :param user_id: User's id
        :return: VideoModel or None
        """
        query = VideoModel.objects.filter(
            ormar.and_(
                id=video_id,
                user=user_id,
            ),
        ).select_related(
            VideoModel.video_properties,  # type: ignore
        )
        try:
            return await query.get()
        except NoMatch:
            return None

    @staticmethod
    async def get_clip(
        clip_id: int,
        user_id: int,
    ) -> ClipModel | None:
        """
        Returns ClipModel with specified video_id and user_id.

        :param clip_id: ClipModel's id
        :param user_id: User's id
        :return: ClipModel or None
        """
        query = ClipModel.objects.filter(
            ormar.and_(
                id=clip_id,
                user=user_id,
            ),
        ).select_related(
            ClipModel.video_properties,  # type: ignore
        )
        try:
            return await query.get()
        except NoMatch:
            return None

    @staticmethod
    async def get_clip_by_key(
        user_id: int,
        clip_key: str,
    ) -> ClipModel | None:
        """
        Returns ClipModel by specified user_id and clip_key.

        :param user_id: User's id
        :param clip_key: Clip Key
        :return: ClipModel or None
        """
        query = ClipModel.objects.filter(
            ormar.and_(
                user=user_id,
                video_key=clip_key,
            ),
        ).select_related(
            ClipModel.video_properties,  # type: ignore
        )
        try:
            return await query.first()
        except NoMatch:
            return None

    @staticmethod
    async def get_video_by_key(
        user_id: int,
        video_key: str,
    ) -> VideoModel | None:
        """
        Returns VideoModel by specified user_id and video_key.

        :param user_id: User's id
        :param video_key: Video Key
        :return: VideoModel or None
        """
        query = VideoModel.objects.filter(
            ormar.and_(
                user=user_id,
                video_key=video_key,
            ),
        ).select_related(
            VideoModel.video_properties,  # type: ignore
        )
        try:
            return await query.get()
        except NoMatch:
            return None

    @staticmethod
    async def get_all_videos(
        user_id: int,
    ) -> List[VideoModel]:
        """
        Returns all VideoModels related to user.

        :param user_id: User's id
        :return: VideoModel's list
        """
        query = VideoModel.objects.filter(VideoModel.user.id == user_id).select_related(
            VideoModel.video_properties,  # type: ignore
        )
        try:
            return await query.all()
        except NoMatch:
            return []

    @staticmethod
    async def get_all_clips(
        user_id: int,
    ) -> List[ClipModel]:
        """
        Returns all ClipModels related to user.

        :param user_id: User's id
        :return: ClipModel's list
        """
        query = ClipModel.objects.filter(ClipModel.user.id == user_id).select_related(
            ClipModel.video_properties,  # type: ignore
        )
        try:
            return await query.all()
        except NoMatch:
            return []

    @staticmethod
    async def take_last_videos(
        user_id: int,
        amount: int,
        select_properties: bool = False,
    ) -> List[VideoModel]:
        """
        Returns last VideoModels related to user.

        :param user_id: User's id
        :param amount: Amount of last VideoModels
        :param select_properties: Option to select related video properties
        :return: VideoModel's list
        """
        query = VideoModel.objects.filter(VideoModel.user.id == user_id)
        if select_properties:
            query = query.select_related(
                VideoModel.video_properties,  # type: ignore
            )

        try:
            return await query.order_by("-id").limit(amount).all()
        except NoMatch:
            return []

    @staticmethod
    async def last_videos_within_days(
        user_id: int,
        days: int,
        amount: int,
    ) -> bool:
        """
        Checks if all last VideoModels related to user are uploaded within specified days.

        :param user_id: User's id
        :param days: Days
        :param amount: Amount of last VideoModels
        :return: bool
        """
        videos = await VideoDAO.take_last_videos(user_id, amount)

        if not videos:
            return False

        return (
            sum(
                1 for video in videos if (datetime.now() - video.uploaded).days < days
            )  # noqa: WPS221
            == amount
        )
