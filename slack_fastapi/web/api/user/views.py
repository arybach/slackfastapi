from fastapi import APIRouter
from fastapi.param_functions import Depends

from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.services.token_handler import TokenHandler
from slack_fastapi.settings import settings
from slack_fastapi.web.api.auth.responses import AuthResponses
from slack_fastapi.web.api.generics.schemas import SuccessResponse
from slack_fastapi.web.api.generics.services import ResponseHandler
from slack_fastapi.web.api.user.schema import (
    TrainedModelsSchema,
    UserClipSettingsSchema,
    UserSchema,
)
from slack_fastapi.web.api.user.services import UserHandler

router = APIRouter()
token_handler = TokenHandler()
user_handler = UserHandler()
response_handler = ResponseHandler()

auth_responses = AuthResponses()


@router.get(
    "",
    response_model=UserSchema,
)
async def get_user_info(
    user_email: str = Depends(token_handler.auth_wrapper),
    user_dao: UserDAO = Depends(),
) -> UserSchema:
    """
    User info endpoint.

    :param user_email: User's email
    :param user_dao: UserDAO
    :return: User's info
    """
    return await user_handler.get_user(
        user_email=user_email,
        user_dao=user_dao,
    )


@router.get(
    "/settings",
    response_model=UserClipSettingsSchema,
)
async def get_clip_settings(
    user_email: str = Depends(token_handler.auth_wrapper),
    user_dao: UserDAO = Depends(),
) -> UserClipSettingsSchema:
    """
    User settings endpoint.

    :param user_email: User's email
    :param user_dao: UserDAO
    :return: User's settings
    """
    return await user_handler.get_clip_settings(
        user_email=user_email,
        user_dao=user_dao,
    )


@router.put(
    "/settings",
    response_model=SuccessResponse,
)
async def update_clip_settings(
    settings_object: UserClipSettingsSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    User settings update endpoint.

    :param settings_object: UserClipSettingsSchema
    :param user_email: User's email
    :param user_dao: UserDAO
    :return: Api message
    """
    await user_handler.update_clip_settings(
        settings=settings_object,
        user_email=user_email,
        user_dao=user_dao,
    )
    return response_handler.success_response(
        msg="Clip settings updated.",
    )


@router.get(
    "/models",
    response_model=TrainedModelsSchema,
)
async def get_trained_models(
    user_email: str = Depends(token_handler.auth_wrapper),
    user_dao: UserDAO = Depends(),
) -> TrainedModelsSchema:
    """
    User available models endpoint.

    :param user_email: User's email
    :param user_dao: UserDAO
    :return: list of available models
    """
    return TrainedModelsSchema(
        models=settings.trained_models,
    )
