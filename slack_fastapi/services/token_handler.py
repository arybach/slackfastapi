from typing import Any, Dict

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt as jose_jwt

from slack_fastapi.db.dao.tokens_dao import TokenDAO
from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.logger.services import LoggerMessages, LoggerMethods
from slack_fastapi.settings import settings
from slack_fastapi.web.api.auth.schema import TokenSchema

bodylog = LoggerMethods.get_bodies_logger()


class TokenHandler:
    """Class for JWT operations."""

    security = HTTPBearer()

    @staticmethod
    def create_access_token(
        data: str,
    ) -> str:
        """
        Create access token.

        :param data: Token data
        :return: Access token
        """
        payload = {
            "exp": settings.jwt_access_expires_at,
            "iat": settings.jwt_creation_time,
            "scope": "access_token",
            "sub": data,
        }
        return jose_jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.algorithm,
        )

    @staticmethod
    def create_refresh_token(
        data: str,
    ) -> str:
        """
        Create refresh token.

        :param data: Token data
        :return: Refresh token
        """
        payload = {
            "exp": settings.jwt_refresh_expires_at,
            "iat": settings.jwt_creation_time,
            "scope": "refresh_token",
            "sub": data,
        }
        return jose_jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.algorithm,
        )

    def get_tokens(
        self,
        identity: str,
    ) -> TokenSchema:
        """
        Get tokens.

        :param identity: User data string
        :return: JWT Tokens
        """
        return TokenSchema(
            access_token=TokenHandler.create_access_token(identity),
            refresh_token=TokenHandler.create_refresh_token(identity),
        )

    @staticmethod
    def decode_token(
        token: str,
        return_field: str = "sub",
    ) -> str | Dict[str, Any]:
        """
        Decode token's data.

        :raises HTTPException: Token expired, Invalid token
        :raises ValueError: If return_field not match 'sub' or 'all'
        :param token: Token
        :param return_field: Field to return, default: sub
        :return: Token data
        """
        try:
            payload = jose_jwt.decode(
                token,
                settings.secret_key,
                algorithms=settings.algorithm,
            )
            if return_field == "sub":
                return payload["sub"]
            elif return_field == "all":
                return payload
            raise ValueError
        except jose_jwt.ExpiredSignatureError:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="TOKEN_EXPIRED",
                    token=token,
                    return_field=return_field,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="TOKEN_EXPIRED",
            )
        except jose_jwt.JWTError:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INVALID_TOKEN",
                    token=token,
                    return_field=return_field,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INVALID_TOKEN",
            )

    @staticmethod
    async def auth_wrapper(
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> str | Dict[str, Any]:
        """
        Authentication wrapper.

        :raises HTTPException: Unauthorized
        :param auth: JWT Headers
        :return: Token data
        """
        token_dao: TokenDAO = TokenDAO()
        if await token_dao.check_token(token=auth.credentials):
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="BLACKLIST_TOKEN",
                    auth=auth,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="BLACKLIST_TOKEN",
            )
        return TokenHandler.decode_token(auth.credentials)

    async def check(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> None:
        """
        Main wrapper for check user in database.

        :raises HTTPException: User not found, not verified
        :param auth: JWT Headers
        """
        email = await self.auth_wrapper(auth)
        user = await UserDAO.get_user(email=email)  # type: ignore
        if user is None:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="USER_NOT_FOUND",
                    auth=auth,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_FOUND",
            )
        if not user.verified:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="USER_NOT_VERIFIED",
                    auth=auth,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_VERIFIED",
            )

    @staticmethod
    async def token_wrapper(
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> str:
        """Wrapper for getting token from header.

        :param auth: JWT Headers
        :return: Token
        """
        return auth.credentials
