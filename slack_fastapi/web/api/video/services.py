import asyncio
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

import aioboto3
import botocore.exceptions  # noqa: WPS301
import ffmpeg
import slackcutter
from fastapi import HTTPException, UploadFile, status
from fastapi.responses import Response

from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.db.dao.videos_dao import VideoDAO
from slack_fastapi.db.models.clip_model import ClipModel
from slack_fastapi.db.models.video_model import VideoModel
from slack_fastapi.logger.services import LoggerMessages, LoggerMethods
from slack_fastapi.services.roles import RoleManager
from slack_fastapi.settings import settings
from slack_fastapi.web.api.auth.helpers import general_access_check
from slack_fastapi.web.api.generics.schemas import IdSchema, IdStrictSchema
from slack_fastapi.web.api.generics.services import Generics
from slack_fastapi.web.api.video.schema import (
    AllClipsSchema,
    AllVideosSchema,
    ClipCreateSchema,
    ClipSchema,
    VideoPropertiesSchema,
    VideoSchema,
)

bodylog = LoggerMethods.get_bodies_logger()


class VideoHandler:
    """Class for media operations."""

    @staticmethod
    async def validate_file(
        file: UploadFile,
        max_size: int = 100000000,
        mime_types: List[str] = None,  # type: ignore
    ) -> bytes:
        """
        Validate a file by checking the size and mime types a.k.a file types.

        :raises HTTPException: UNSUPPORTED_FILE_TYPE
        :raises HTTPException: LARGE_FILE_EXCEPTION
        :param file: UploadFile
        :param max_size: Maximum file size in bytes
        :param mime_types: Allowed mime types
        :return: bytes of file
        """
        if mime_types and file.content_type not in mime_types:
            await file.seek(0)
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="UNSUPPORTED_FILE_TYPE",
                    file_type=file.content_type,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="UNSUPPORTED_FILE_TYPE",
            )

        sized_file = await file.read()

        if max_size:
            len_size = len(sized_file)
            if len_size > max_size:
                await file.seek(0)
                bodylog.debug(
                    LoggerMessages.exception(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="LARGE_FILE_EXCEPTION",
                        support_size=max_size,
                        current_size=len_size,
                        file_type=file.content_type,
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="LARGE_FILE_EXCEPTION",
                )

        await file.seek(0)
        return sized_file

    @staticmethod
    async def s3_object_by_key(key: str, resource: Any) -> Any:
        """
        Finds and returns s3 object with corresponding key.

        :raises HTTPException: S3_OBJECT_EXTRACTION_FAILED
        :param key: Media Key
        :param resource: S3 session resource
        :return: S3 object
        """
        try:
            s3_object = await resource.Object(settings.s3_bucket, key)
            await s3_object.load()
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "404":
                return False
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="S3_OBJECT_EXTRACTION_FAILED",
                    key=key,
                    error_type=ex,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"S3_OBJECT_EXTRACTION_FAILED, ERROR_TYPE: {ex}",
            )
        return s3_object

    @staticmethod
    async def s3_upload_file(
        key: str,
        file: Dict[str, Any],
        acl: str,
        s3_bucket: Any = None,  # type: ignore
    ) -> None:
        """
        Uploads local media to s3 bucket.

        file keys:
        file["body"] - bytes of media;
        file["content_type"] - mime type of media (video/mp4 etc.)

        :param key: Media key and future path of media file in s3 bucket
        :param file: Dictionary that contains atleast 2 essencial keys:
        :param acl: Access rights to media ("private", "public-read" etc.)
        :param s3_bucket: S3 session resource bucket
        """
        if s3_bucket:
            await s3_bucket.put_object(
                ACL=acl,
                Key=key,
                Body=file["body"],
                ContentType=file["content_type"],
            )
        else:
            session = aioboto3.Session()
            async with session.resource(
                "s3",
                region_name=settings.s3_region,
                endpoint_url=settings.s3_endpoint_url,
            ) as resource:
                s3_bucket = await resource.Bucket(settings.s3_bucket)
                await s3_bucket.put_object(
                    ACL=acl,
                    Key=key,
                    Body=file["body"],
                    ContentType=file["content_type"],
                )

    @staticmethod
    async def s3_upload_media(  # noqa: WPS210
        video_dict: Dict[str, Any] = None,  # type: ignore
        audio_dict: Dict[str, Any] = None,  # type: ignore
    ) -> Tuple[bool, bool]:
        """
        Wrapper to upload media (video and audio) to s3 bucket.

        Dictionaries must contain atleast 3 essencial keys:
        dict["key"] - Media key and future path of media file in s3 bucket;
        dict["body"] - bytes of media;
        dict["content_type"] - mime type of media (video/mp4 etc.).
        first return bool value relates to the success of video upload;
        second return bool value relates to the success of audio upload

        :param video_dict: Dictionary that contains atleast 3 essencial keys
        :param audio_dict: Dictionary that contains atleast 3 essencial keys
        :return: (bool, bool), each boolean corresponding media upload success;
        """
        tasks = []
        session = aioboto3.Session()
        async with session.resource(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        ) as resource:
            s3_bucket = await resource.Bucket(settings.s3_bucket)

            video_created = False
            audio_created = False

            video_exists = True
            if video_dict:
                video_exists = await VideoHandler.s3_object_by_key(
                    key=video_dict["key"],
                    resource=resource,
                )

            audio_exists = True
            if audio_dict:
                audio_exists = await VideoHandler.s3_object_by_key(
                    key=audio_dict["key"],
                    resource=resource,
                )

            if not video_exists:
                tasks.append(
                    asyncio.ensure_future(
                        VideoHandler.s3_upload_file(
                            video_dict["key"],
                            video_dict,
                            "private",
                            s3_bucket,
                        ),
                    ),
                )
                video_created = True

            if not audio_exists:
                tasks.append(
                    asyncio.ensure_future(
                        VideoHandler.s3_upload_file(
                            audio_dict["key"],
                            audio_dict,
                            "private",
                            s3_bucket,
                        ),
                    ),
                )
                audio_created = True

            if tasks:
                await asyncio.gather(*tasks)

            return video_created, audio_created

    @staticmethod
    async def extract_video_properties(  # noqa: WPS210
        video_dict: Dict[str, Any],
        audio_content_type: str = None,  # type: ignore
    ) -> VideoPropertiesSchema:
        """
        Extracts video properties to VideoPropertiesSchema from video_dict.

        video_dict["md5name"] - you'll get it from VideoHandler.generate_md5_filename;
        video_dict["body"] - contain bytes object of your file;
        video_dict["content_type"] - mime type of your file (UploadFile.content_type);

        :param video_dict: Dictionary that contains atleast 3 essencial keys:
        :param audio_content_type: Audio content type (mime type) if attached audio exists
        :return: VideoPropertiesSchema
        """
        path = Path(settings.temp_dir)
        path.mkdir(parents=True, exist_ok=True)

        video_path = path.joinpath(video_dict["md5name"])

        with open(video_path, "wb") as f:  # type: ignore # noqa WPS111
            f.write(video_dict["body"])  # type: ignore

        for codec in ffmpeg.probe(video_path)["streams"]:
            if codec["codec_type"] == "video":
                vid = codec

        if video_dict["content_type"] == "video/webm":
            dt = (
                datetime.strptime(
                    vid["tags"]["DURATION"][:-3],
                    "%H:%M:%S.%f",  # noqa: WPS221
                ),
            )
            video_duration = (
                timedelta(
                    hours=dt.hour,  # type: ignore
                    minutes=dt.minute,  # type: ignore
                    seconds=dt.second,  # type: ignore
                    microseconds=dt.microsecond,  # type: ignore
                ).total_seconds()
                * 1000
            )
        elif video_dict["content_type"] == "video/mp4":
            video_duration = int(float(vid["duration"]) * 1000000)  # noqa: WPS432

        video_path.unlink()

        return VideoPropertiesSchema(
            duration=video_duration,
            video_content_type=video_dict["content_type"],
            audio_content_type=audio_content_type,
            frame_width=vid["width"],
            frame_height=vid["height"],
            size=len(video_dict["body"]),
        )

    @staticmethod
    async def update_model_audio_with_key_validation(
        user_id: int,
        video_model: VideoModel,
        audio_key: str,
        audio_content_type: str,
        video_dao: VideoDAO,
    ) -> None:
        """
        Updates VideoModel audio key and deletes audio from s3 bucket if there is only 1 link.

        :param user_id: User's id
        :param video_model: VideoModel:
        :param audio_key: Media key, path of media file in s3 bucket
        :param audio_content_type: Mime type of audio:
        :param video_dao: VideoDAO:
        """
        audio_links_count = await video_dao.get_audio_key_links(
            user_id=user_id,
            audio_key=video_model.audio_key,
        )

        if audio_links_count == 1:
            session = aioboto3.Session()
            async with session.resource(
                "s3",
                region_name=settings.s3_region,
                endpoint_url=settings.s3_endpoint_url,
            ) as resource:
                obj = await VideoHandler.s3_object_by_key(
                    key=video_model.audio_key,
                    resource=resource,
                )

                await obj.delete()

        await video_model.update(
            audio_key=audio_key,
        )
        await video_model.video_properties.update(
            audio_content_type=audio_content_type,
        )

    @staticmethod
    async def s3_object_exists(
        key: str,
    ) -> bool:
        """
        Returns True if object with specified key exists in s3 bucket.

        :param key: Media key, path of media file in s3 bucket.
        :return: bool
        """
        session = aioboto3.Session()
        async with session.resource(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        ) as resource:
            obj = await VideoHandler.s3_object_by_key(
                key=key,
                resource=resource,
            )

        return bool(obj)

    @staticmethod
    async def handle_models(  # noqa: WPS211, WPS217
        user_id: int,
        video_dict: Dict[str, Any],
        audio_dict: Dict[str, Any],
        video_created: bool,
        audio_created: bool,
        video_dao: VideoDAO,
    ) -> VideoModel:
        """
        Creates/updates entries in DB depending on video/audio created states.

        Dicts must contain atleas 3 essential keys:
        dict["name"] - media name (for video_dict only);
        dict["key"] - media key;
        dict["content_type"] - mime type of media;

        :param user_id: User's id
        :param video_dict: Dictionary with video information
        :param audio_dict: Dictionary with audio information
        :param video_created: Was video uploaded to bucket previously?
        :param audio_created: Was audio uploaded to bucket previously?
        :param video_dao: VideoDAO
        :return: VideoModel
        """
        audio_content_type = audio_dict["content_type"] if audio_dict else None
        properties_object = await VideoHandler.extract_video_properties(
            video_dict=video_dict,
            audio_content_type=audio_content_type,
        )

        video_dict = {
            "user": user_id,
            "name": video_dict["name"],
            "video_key": video_dict["key"],
            "audio_key": audio_dict["key"] if audio_dict else None,
        }

        if (not video_created) and audio_created:
            video_model = await video_dao.get_video_by_key(
                user_id=user_id,
                video_key=video_dict["video_key"],
            )
            await VideoHandler.update_model_audio_with_key_validation(
                user_id=user_id,
                video_model=video_model,  # type: ignore
                audio_key=video_dict["audio_key"],
                audio_content_type=audio_content_type,
                video_dao=video_dao,
            )

        elif (not video_created) and (not audio_created):
            video_model = await video_dao.get_video_by_key(
                user_id=user_id,
                video_key=video_dict["video_key"],
            )
            if video_model and video_model.audio_key:
                if (
                    video_dict["audio_key"]
                    and video_model.audio_key != video_dict["audio_key"]
                ):
                    await VideoHandler.update_model_audio_with_key_validation(
                        user_id=user_id,
                        video_model=video_model,
                        audio_key=video_dict["audio_key"],
                        audio_content_type=audio_content_type,
                        video_dao=video_dao,
                    )

        else:
            video_model = await video_dao.create_video_model(
                video_dict=video_dict,
                properties_object=properties_object,
            )

        return video_model  # type: ignore

    @staticmethod
    async def generate_media_key(
        user_email: str,
        md5name: str,
        is_clip: bool = False,
    ) -> str:
        """
        Generate media key.

        :param user_email: User's id
        :param md5name: md5name (out of bytes) of media file
        :param is_clip: Do key belongs to the clip?
        :return: Media key
        """
        user_folder = Generics.string2md5(user_email)
        prefix = settings.s3_prefix if settings.s3_prefix else ""

        # Determine the type of content (clip or not)
        content_type = "clips" if is_clip else "content"

        return f"{user_folder}/{prefix}/{md5name}/{content_type}"

    @staticmethod
    async def generate_md5_filename(file: bytes, filename: str) -> str:
        """
        Generate md5name.

        :param file: bytes of file
        :param filename: name of the file (with extension)
        :return: md5name
        """
        name = Generics.bytes2md5(file)
        extension = filename.split(".")[-1]
        return f"{name}.{extension}"

    @staticmethod
    async def upload_video(
        video_file: UploadFile,
        audio_file: Optional[UploadFile],  # Marking it as optional
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> IdSchema:
        """
        Uploads media to s3 bucket, makes entries in DB.

        :param video_file: UploadFile
        :param audio_file: Optional UploadFile
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        :return: IdSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        if RoleManager.is_basic(user.role):  # type: ignore
            await RoleManager.basic.restriction_check(
                user.id,  # type: ignore
                video_dao,
            )

        # Process Video File
        video_body = await VideoHandler.validate_file(
            video_file,
            mime_types=[
                "video/mp4",
                "video/webm",
            ],
        )
        video_md5name = await VideoHandler.generate_md5_filename(
            file=video_body,
            filename=video_file.filename,
        )
        video_dict = {
            "body": video_body,
            "content_type": video_file.content_type,
            "name": video_file.filename,
            "md5name": video_md5name,
            "key": await VideoHandler.generate_media_key(
                user_email=user_email,
                md5name=video_md5name,
            ),
        }

        # Process Audio File if provided
        audio_dict = {}
        if audio_file:
            audio_body = await VideoHandler.validate_file(
                audio_file,
                max_size=20000000,  # noqa: WPS432
                mime_types=[
                    "audio/mpeg",
                ],
            )
            audio_md5name = await VideoHandler.generate_md5_filename(
                file=audio_body,
                filename=audio_file.filename,
            )
            audio_dict = {
                "body": audio_body,
                "content_type": audio_file.content_type,
                "name": audio_file.filename,
                "md5name": audio_md5name,
                "key": await VideoHandler.generate_media_key(
                    user_email=user_email,
                    md5name=audio_md5name,
                ),
            }

        # Upload to S3
        uploaded = await VideoHandler.s3_upload_media(
            video_dict=video_dict,
            audio_dict=audio_dict
            if audio_dict
            else {},  # Pass empty dict if audio_dict is None
        )

        # Handle DB operations
        video_model = await VideoHandler.handle_models(
            user_id=user.id,  # type: ignore
            video_dict=video_dict,
            audio_dict=audio_dict
            if audio_dict
            else {},  # Pass empty dict if audio_dict is None
            video_created=uploaded[0],
            audio_created=uploaded[1] if audio_dict else False,
            video_dao=video_dao,
        )

        # Check if video_model is not None before trying to access its id
        if video_model is None:
            raise HTTPException(status_code=500, detail="Failed to create video model")
        else:
            return IdSchema(id=video_model.id)

    @staticmethod
    async def get_all_videos(
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> AllVideosSchema:
        """
        Returns AllVideosSchema.

        :param user_email: UserUpdateClipSettingsSchema's dict
        :param video_dao: User's email
        :param user_dao: UserDAO
        :return: IdSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        videos = await video_dao.get_all_videos(
            user_id=user.id,  # type: ignore
        )

        schema_list = []

        for video in videos:
            schema_list.append(
                VideoSchema(
                    id=video.id,
                    video_name=video.name,
                    properties=VideoPropertiesSchema(
                        duration=video.video_properties.duration,
                        video_content_type=video.video_properties.video_content_type,
                        audio_content_type=video.video_properties.audio_content_type,
                        frame_width=video.video_properties.frame_width,
                        frame_height=video.video_properties.frame_height,
                        size=video.video_properties.size,
                    ),
                ),
            )

        return AllVideosSchema(
            videos=schema_list,
        )

    @staticmethod
    async def get_all_clips(
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> AllClipsSchema:
        """
        Returns AllClipsSchema.

        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        :return: AllClipsSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        videos = await video_dao.get_all_clips(
            user_id=user.id,  # type: ignore
        )

        schema_list = []

        for video in videos:
            schema_list.append(
                ClipSchema(
                    id=video.id,
                    video_name=video.name,
                    properties=VideoPropertiesSchema(
                        duration=video.video_properties.duration,
                        video_content_type=video.video_properties.video_content_type,
                        frame_width=video.video_properties.frame_width,
                        frame_height=video.video_properties.frame_height,
                        size=video.video_properties.size,
                    ),
                    link=video.video_key,
                ),
            )

        return AllClipsSchema(
            clips=schema_list,
        )

    @staticmethod
    async def get_video_model(
        video_id: int,
        user_id: int,
        video_dao: VideoDAO,
        is_clip: bool = False,
    ) -> VideoModel | ClipModel:
        """
        Returns VideoModel or ClipModel.

        :raises HTTPException: VIDEO_NOT_FOUND
        :param video_id: Video's id
        :param user_id: User's id
        :param video_dao: VideoDAO
        :param is_clip: Get ClipModel instead of VideoModel?
        :return: VideoModel or ClipModel
        """
        if is_clip:
            video_model = await video_dao.get_clip(
                clip_id=video_id,
                user_id=user_id,
            )
        else:
            video_model = await video_dao.get_video(  # type: ignore
                video_id=video_id,
                user_id=user_id,
            )

        if not video_model:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="VIDEO_NOT_FOUND",
                    video_id=video_id,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="VIDEO_NOT_FOUND",
            )

        return video_model

    @staticmethod
    async def s3_operate_objects_by_model(
        video_model: VideoModel | ClipModel,
        callback: Callable[[List[Any]], Any],
    ) -> Any:
        """
        Gets s3 objects related with the Model and passes them through callback function.

        :param video_model: VideoModel or ClipModel
        :param callback: Async function which will be called with passed S3 objects
        :return: Output of callback
        """
        session = aioboto3.Session()
        async with session.resource(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        ) as resource:
            objects = []

            video_object = await VideoHandler.s3_object_by_key(
                key=video_model.video_key,
                resource=resource,
            )
            if video_object:
                objects.append(video_object)

            try:
                if video_model.audio_key:
                    audio_object = await VideoHandler.s3_object_by_key(
                        key=video_model.audio_key,
                        resource=resource,
                    )
                    if audio_object:
                        objects.append(audio_object)  # noqa: WPS220
            except AttributeError:
                return await callback(objects)

            return await callback(objects)

    @staticmethod
    async def delete_video(  # noqa: WPS217
        id_object: IdStrictSchema,
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> None:
        """
        Deletes video (and audio if exists) from s3 bucket and DB.

        :param id_object: IdStrictSchema
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        video_model = await VideoHandler.get_video_model(
            video_id=id_object.id,
            user_id=user.id,  # type: ignore
            video_dao=video_dao,
        )

        async def callback(objects: Any) -> None:  # noqa: WPS430
            for obj in objects:
                await obj.delete()

        await VideoHandler.s3_operate_objects_by_model(
            video_model=video_model,
            callback=callback,
        )

        await video_model.delete()
        await video_model.video_properties.delete()

    @staticmethod
    async def delete_clip(  # noqa: WPS217
        id_object: IdStrictSchema,
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> None:
        """
        Deletes clip from s3 bucket and DB.

        :param id_object: IdStrictSchema
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        clip_model = await VideoHandler.get_video_model(
            video_id=id_object.id,
            user_id=user.id,  # type: ignore
            video_dao=video_dao,
            is_clip=True,
        )

        async def callback(objects: Any) -> None:  # noqa: WPS430
            obj = objects[0]
            await obj.delete()

        await VideoHandler.s3_operate_objects_by_model(
            video_model=clip_model,
            callback=callback,
        )

        await clip_model.delete()
        await clip_model.video_properties.delete()

    @staticmethod
    async def create_clip(  # noqa: WPS217, WPS210, WPS231, C901, WPS213
        clip_creation_object: ClipCreateSchema,
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> IdSchema:
        """
        Generates clip, uploades it to S3 bucket and creates DB record.

        :raises HTTPException: CREATION_IN_PROCESS
        :raises HTTPException: SLACKCUTTER_ERROR
        :param clip_creation_object: ClipCreateSchema
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        :return: IdSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email, select_related=True),
        )

        temp_path = Path(
            settings.temp_dir,
            Generics.string2md5(user_email),
        )

        if temp_path.exists():
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="CREATION_IN_PROCESS",
                    clip_creation_object=clip_creation_object.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CREATION_IN_PROCESS",
            )

        video_model = await VideoHandler.get_video_model(
            video_id=clip_creation_object.id,
            user_id=user.id,  # type: ignore
            video_dao=video_dao,
        )

        async def callback(  # noqa: WPS430, WPS210, WPS234
            objects: Any,
        ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:  # noqa: WPS221
            video_dict = None
            audio_dict = None

            path = Path(
                settings.temp_dir,
                Generics.string2md5(user_email),
            )

            os.makedirs(path.resolve())

            for obj in objects:
                unix = Generics.get_unixstring()
                content_type = await obj.content_type
                current_content, extension = content_type.split("/")
                filename = f"{unix}.{extension}"

                filepath = path.joinpath(filename)

                await obj.download_file(filepath.as_posix())

                with open(filepath.resolve(), "rb") as f:  # type: ignore # noqa WPS111
                    body = f.read()  # type: ignore

                    file = {
                        "name": filename,
                        "path": filepath,
                        "body": body,
                        "content_type": content_type,
                    }

                    if current_content == "video":
                        video_dict = file  # noqa: WPS220
                    elif current_content == "audio":
                        audio_dict = file  # noqa: WPS220

            return video_dict, audio_dict

        video_dict, audio_dict = await VideoHandler.s3_operate_objects_by_model(
            video_model=video_model,
            callback=callback,
        )

        slackcutter.config.temp_folder = temp_path.joinpath("slack").as_posix()  # type: ignore
        slackcutter.config.output_folder = temp_path.joinpath("output").as_posix()  # type: ignore

        clip_name = clip_creation_object.output_name + ".mp4"  # noqa: WPS336

        try:
            slack = slackcutter.SlackCutter(  # type: ignore
                source_name=temp_path.joinpath(video_dict["name"]).as_posix(),
                trained_model_name=user.clip_settings.trained_model,  # type: ignore
                output_name=clip_name,
                max_seconds_length=user.clip_settings.max_seconds_lenght,  # type: ignore
                model_threshold=user.clip_settings.model_threshold,  # type: ignore
                sound_check=user.clip_settings.sound_check,  # type: ignore
                noice_threshold=list(
                    map(int, user.clip_settings.noice_threshold.split(",")),  # type: ignore
                ),
                audio_threshold=list(
                    map(int, user.clip_settings.audio_threshold.split(",")),  # type: ignore
                ),
                median_hit_modificator=user.clip_settings.median_hit_modificator,  # type: ignore
                crop_interval=list(map(int, user.clip_settings.crop_interval.split(","))),  # type: ignore
            )
        except Exception as e:
            shutil.rmtree(temp_path.as_posix())
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SLACKCUTTER_ERROR, ERROR TYPE: {e}",
            )

        try:
            slack.make_clip()
        except Exception as ex:
            shutil.rmtree(temp_path.as_posix())

            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SLACKCUTTER_ERROR",
                    clip_creation_object=clip_creation_object.dict(),
                    error_type=ex,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SLACKCUTTER_ERROR, ERROR TYPE: {ex}",
            )

        with open(temp_path.joinpath("output", clip_name).as_posix(), "rb") as f:
            clip_body = f.read()

        shutil.rmtree(temp_path.as_posix())

        clip_dict = {
            "name": clip_name,
            "md5name": await VideoHandler.generate_md5_filename(
                file=clip_body,
                filename=clip_name,
            ),
            "body": clip_body,
            "content_type": "video/mp4",
        }
        clip_dict["key"] = await VideoHandler.generate_media_key(
            user_email=user_email,
            md5name=clip_dict["md5name"],  # type: ignore
            is_clip=True,
        )

        clip_key = await VideoHandler.generate_media_key(
            user_email=user_email,
            md5name=clip_dict["md5name"],  # type: ignore
            is_clip=True,
        )
        object_exists = await VideoHandler.s3_object_exists(
            key=clip_key,
        )

        if not object_exists:
            await VideoHandler.s3_upload_file(
                key=clip_dict["key"],  # type: ignore
                file=clip_dict,
                acl="private",
            )

        clip_model = None

        if object_exists:
            clip_model = await video_dao.get_clip_by_key(
                user_id=user.id,  # type: ignore
                clip_key=clip_key,
            )

        if not clip_model:
            clip_properties = await VideoHandler.extract_video_properties(
                video_dict=clip_dict,
            )

            clip_model = await video_dao.create_clip_model(
                clip_dict={
                    "user": user.id,  # type: ignore
                    "name": clip_name,
                    "video_key": clip_dict["key"],
                },
                properties_object=clip_properties,
            )

        return IdSchema(
            id=clip_model.id,
        )

    @staticmethod
    async def download_video(  # noqa: WPS210
        id_object: IdStrictSchema,
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> Response:
        """
        Downloads video from S3 bucket and returns it.

        :param id_object: IdStrictSchema
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        :return: Response
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        video_model = await VideoHandler.get_video_model(
            video_id=id_object.id,
            user_id=user.id,  # type: ignore
            video_dao=video_dao,
        )

        async def callback(objects: Any) -> Tuple[Path, Any]:  # noqa: WPS430
            obj = objects[0]
            content_type = await obj.content_type
            unix = Generics.get_unixstring()
            extension = content_type.split("/")[-1]
            path = Path(settings.temp_dir, "downloads", f"{unix}.{extension}")

            if not path.parent.exists():
                os.makedirs(path.parent.as_posix())

            await obj.download_file(path.as_posix())
            return path, content_type

        path, content_type = await VideoHandler.s3_operate_objects_by_model(
            video_model=video_model,
            callback=callback,
        )

        with open(path.as_posix(), mode="rb") as f:
            file = f.read()

        response = Response(
            content=file,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{quote(video_model.name)}"',  # noqa: WPS237
            },
        )
        path.unlink()

        return response

    @staticmethod
    async def download_clip(  # noqa: WPS210
        id_object: IdStrictSchema,
        user_email: str,
        video_dao: VideoDAO,
        user_dao: UserDAO,
    ) -> Response:
        """
        Downloads clip from S3 bucket and returns it.

        :param id_object: IdStrictSchema
        :param user_email: User's email
        :param video_dao: VideoDAO
        :param user_dao: UserDAO
        :return: Response
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        video_model = await VideoHandler.get_video_model(
            video_id=id_object.id,
            user_id=user.id,  # type: ignore
            video_dao=video_dao,
            is_clip=True,
        )

        async def callback(objects: Any) -> Tuple[Path, Any]:  # noqa: WPS430
            obj = objects[0]
            content_type = await obj.content_type
            unix = Generics.get_unixstring()
            extension = content_type.split("/")[-1]
            path = Path(settings.temp_dir, "downloads", f"{unix}.{extension}")

            if not path.parent.exists():
                os.makedirs(path.parent.as_posix())

            await obj.download_file(path.as_posix())
            return path, content_type

        path, content_type = await VideoHandler.s3_operate_objects_by_model(
            video_model=video_model,
            callback=callback,
        )

        with open(path.as_posix(), mode="rb") as f:
            file = f.read()

        response = Response(
            content=file,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{quote(video_model.name)}"',  # noqa: WPS237
            },
        )
        path.unlink()

        return response
