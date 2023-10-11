from fastapi import HTTPException, status

from slack_fastapi.db.models.user_model import UserModel
from slack_fastapi.logger.services import LoggerMessages, LoggerMethods

bodylog = LoggerMethods.get_bodies_logger()


def general_access_check(user: UserModel | None) -> UserModel:
    """
    General access check.

    :param user: UserModel
    :raises HTTPException: Access denied
    :return: UserModel
    """
    if not user:
        bodylog.debug(
            LoggerMessages.exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="NO_SUCH_USER",
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NO_SUCH_USER",
        )

    if not user.verified:
        bodylog.debug(
            LoggerMessages.exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_VERIFIED",
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="USER_NOT_VERIFIED",
        )

    if not user.set_up:
        bodylog.debug(
            LoggerMessages.exception(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_SET_UP",
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="USER_NOT_SET_UP",
        )

    return user
