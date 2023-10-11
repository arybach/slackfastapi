from fastapi import APIRouter, File, UploadFile
from fastapi.param_functions import Depends
from fastapi.responses import Response

from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.db.dao.videos_dao import VideoDAO
from slack_fastapi.services.token_handler import TokenHandler
from slack_fastapi.web.api.auth.responses import AuthResponses
from slack_fastapi.web.api.generics.schemas import (
    IdSchema,
    IdStrictSchema,
    SuccessResponse,
)
from slack_fastapi.web.api.generics.services import ResponseHandler
from slack_fastapi.web.api.user.services import UserHandler
from slack_fastapi.web.api.video.schema import (
    AllClipsSchema,
    AllVideosSchema,
    ClipCreateSchema,
)
from slack_fastapi.web.api.video.services import VideoHandler

router = APIRouter()
token_handler = TokenHandler()
user_handler = UserHandler()
video_handler = VideoHandler()
response_handler = ResponseHandler()

auth_responses = AuthResponses()


@router.post(
    "/video",
    response_model=IdSchema,
)
async def upload_files(
    video_file: UploadFile = File(),
    audio_file: UploadFile = File(None),
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> IdSchema:
    """
    Endpoint to upload media files and create DB entries.

    :param video_file: Video UploadFile
    :param audio_file: Audio UploadFile
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: VideoModel's id
    """
    return await video_handler.upload_video(
        video_file=video_file,
        audio_file=audio_file,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )


@router.delete(
    "/video",
    response_model=SuccessResponse,
)
async def delete_video(
    id_object: IdStrictSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Endpoint to delete video entries from S3 bucket and DB.

    :param id_object: IdStrictSchema with VideoModel's id
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: Api message
    """
    await video_handler.delete_video(
        id_object=id_object,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )

    return response_handler.success_response(
        msg="Video successefuly deleted.",
    )


@router.get(
    "/videos",
    response_model=AllVideosSchema,
)
async def get_videos(
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> AllVideosSchema:
    """
    Endpoint to get all user's uploaded video information.

    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: AllVideosSchema
    """
    return await video_handler.get_all_videos(
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )


@router.post(
    "/clip",
    response_model=IdSchema,
)
async def create_clip(
    clip_creation_object: ClipCreateSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> IdSchema:
    """
    Endpoint to create clip and made entries in S3 bucket and DB.

    :param clip_creation_object: VideoModel's id and future clip name
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: ClipModel's id
    """
    return await video_handler.create_clip(
        clip_creation_object=clip_creation_object,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )


@router.delete(
    "/clip",
    response_model=SuccessResponse,
)
async def delete_clip(
    id_object: IdStrictSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Endpoint to delete clip entries from S3 bucket and DB.

    :param id_object: IdStrictSchema with ClipModel's id
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: Api message
    """
    await video_handler.delete_clip(
        id_object=id_object,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )

    return response_handler.success_response(
        msg="Clip successefuly deleted.",
    )


@router.get(
    "/clips",
    response_model=AllClipsSchema,
)
async def get_clips(
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> AllClipsSchema:
    """
    Endpoint to get all user's uploaded clip information.

    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: AllClipsSchema
    """
    return await video_handler.get_all_clips(
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )


@router.post(
    "/video/download",
    response_class=Response,
)
async def download_video(
    id_object: IdStrictSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> Response:
    """
    Endpoint to response with downloaded user video.

    :param id_object: IdStrictSchema with VideoModel's id
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: Video file
    """
    return await video_handler.download_video(
        id_object=id_object,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )


@router.post(
    "/clip/download",
    response_class=Response,
)
async def download_clip(
    id_object: IdStrictSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    video_dao: VideoDAO = Depends(),
    user_dao: UserDAO = Depends(),
) -> Response:
    """
    Endpoint to response with downloaded user video.

    :param id_object: IdStrictSchema with ClipModel's id
    :param user_email: User's email
    :param video_dao: VideoDAO
    :param user_dao: UserDAO
    :return: Video file
    """
    return await video_handler.download_clip(
        id_object=id_object,
        user_email=user_email,
        video_dao=video_dao,
        user_dao=user_dao,
    )
