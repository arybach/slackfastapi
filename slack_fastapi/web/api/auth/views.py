from fastapi import APIRouter
from fastapi.param_functions import Depends

from slack_fastapi.db.dao.tokens_dao import TokenDAO
from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.services.token_handler import TokenHandler
from slack_fastapi.web.api.auth.responses import AuthResponses
from slack_fastapi.web.api.auth.schema import (
    CodeVerificationSchema,
    TokenSchema,
    UserAuthorizationSchema,
    UserEmailSchema,
    UserPasswordRecoverSchema,
    UserPasswordUpdateSchema,
    UserSetUpSchema,
)
from slack_fastapi.web.api.auth.services import AuthHandler
from slack_fastapi.web.api.generics.schemas import SuccessResponse
from slack_fastapi.web.api.generics.services import ResponseHandler

router = APIRouter()
auth_handler = AuthHandler()
token_handler = TokenHandler()
response_handler = ResponseHandler()

auth_responses = AuthResponses()


@router.post(
    "/register",
    response_model=SuccessResponse,
    responses=auth_responses.registration_responses,
)
async def register(
    email_object: UserEmailSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    User registration endpoint.

    :param email_object: Email object
    :param user_dao: DAO of user model
    :return: Api message
    """
    await auth_handler.registration_handler(email_object, user_dao)
    return response_handler.success_response(
        msg="User registered. Awaiting email confirmation.",
    )


@router.post(
    "/setup",
    response_model=TokenSchema,
)
async def set_up(
    set_up_object: UserSetUpSchema,
    user_dao: UserDAO = Depends(),
) -> TokenSchema:
    """
    User final registration endpoint.

    :param set_up_object: SetUp object
    :param user_dao: DAO of user model
    :return: Api message
    """
    return await auth_handler.set_up_handler(set_up_object, user_dao)


@router.post(
    "/password_update",
    response_model=SuccessResponse,
)
async def password_update(
    password_object: UserPasswordUpdateSchema,
    user_email: str = Depends(token_handler.auth_wrapper),
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    User password update endpoint.

    :param password_object: Password object
    :param user_email: User email (token)
    :param user_dao: DAO of user model
    :return: Api message
    """
    await auth_handler.password_update_handler(password_object, user_email, user_dao)
    return response_handler.success_response(
        msg="Password updated",
    )


@router.post(
    "/login",
    response_model=TokenSchema,
    responses=auth_responses.login_responses,
)
async def login(
    user_object: UserAuthorizationSchema,
    user_dao: UserDAO = Depends(),
) -> TokenSchema:
    """
    User login endpoint.

    :param user_object: User object
    :param user_dao: DAO of user model
    :return: JWT Tokens
    """
    return await auth_handler.login_handler(user_object, user_dao=user_dao)


@router.post(
    "/logout",
    response_model=SuccessResponse,
    responses=auth_responses.jwt_responses,
)
async def logout(
    token: str = Depends(token_handler.token_wrapper),
    token_dao: TokenDAO = Depends(),
) -> SuccessResponse:
    """
    User logout endpoint.

    :param token: Token
    :param token_dao: DAO for token model
    :return: Api message
    """
    await auth_handler.logout_handler(token, token_dao)
    return response_handler.success_response(
        msg="Successful logout",
    )


@router.post(
    "/password_recover",
    response_model=SuccessResponse,
    responses=auth_responses.passcode_responses,
)
async def generate_passcode(
    email_object: UserEmailSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Password recover endpoint (generates code).

    :param email_object: UserEmailSchema
    :param user_dao: DAO of user model
    :return: Api message
    """
    await auth_handler.passcode_handler(email_object.email, user_dao)
    return response_handler.success_response(
        msg="Passcode was sent",
    )


@router.put(
    "/password_recover",
    response_model=SuccessResponse,
    responses=auth_responses.password_recover_responses,
)
async def password_recover(
    recover_data: UserPasswordRecoverSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Password recover endpoint (changes password).

    :param recover_data: UserPasswordRecoverSchema
    :param user_dao: DAO of user model
    :return: Api message
    """
    await auth_handler.password_recover_handler(recover_data, user_dao)
    return response_handler.success_response(
        msg="Password was changed.",
    )


@router.post(
    "/passcode_verification",
    response_model=SuccessResponse,
    responses=auth_responses.password_recover_responses,
)
async def passcode_verification(
    to_verify: CodeVerificationSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Passcode verification endpoint.

    :param to_verify: Data to verify (email, passcode)
    :param user_dao: DAO of user model
    :return: Api message
    """
    await auth_handler.passcode_verify_handler(to_verify, user_dao)
    return response_handler.success_response(
        msg="Passcode is correct.",
    )


@router.post(
    "/email/confirm",
    response_model=SuccessResponse,
    responses=auth_responses.confirmation_responses,
)
async def email_confirmation(
    verification_object: CodeVerificationSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Email verification endpoint.

    :param verification_object: UserVerificationSchema
    :param user_dao: UserDAO
    :return: Api message.
    """
    await auth_handler.confirmation_handler(verification_object, user_dao)
    return response_handler.success_response(
        msg="OK",
    )


@router.post(
    "/email/resend",
    response_model=SuccessResponse,
    responses=auth_responses.resend_responses,
)
async def email_resend(
    email_object: UserEmailSchema,
    user_dao: UserDAO = Depends(),
) -> SuccessResponse:
    """
    Email resend endpoint.

    :param email_object: UserEmailSchema
    :param user_dao: UserDAO
    :return: Api message
    """
    await auth_handler.resend_handler(email_object.email, user_dao)
    return response_handler.success_response(
        msg="Confirmation code was sent",
    )


@router.post(
    "/refresh",
    response_model=TokenSchema,
    responses=auth_responses.jwt_responses,
)
async def refresh_tokens(
    requires_token: str = Depends(token_handler.auth_wrapper),
) -> TokenSchema:
    """
    Refreshes the user tokens.

    :param requires_token: username
    :return: TokenSchema
    """
    return token_handler.get_tokens(identity=requires_token)
