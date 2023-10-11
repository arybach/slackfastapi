import secrets
import string
from typing import Any, Dict

from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema
from passlib.context import CryptContext

from slack_fastapi.db.dao.tokens_dao import TokenDAO
from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.logger.services import LoggerMessages, LoggerMethods
from slack_fastapi.services.token_handler import TokenHandler
from slack_fastapi.settings import settings
from slack_fastapi.web.api.auth.helpers import general_access_check
from slack_fastapi.web.api.auth.schema import (
    CodeVerificationSchema,
    TokenSchema,
    UserAuthorizationSchema,
    UserEmailSchema,
    UserPasswordRecoverSchema,
    UserPasswordUpdateSchema,
    UserSetUpSchema,
)
from slack_fastapi.web.api.user.schema import UserClipSettingsSchema

bodylog = LoggerMethods.get_bodies_logger()
token_handler = TokenHandler()


class MailHandler:
    """Class for email operations."""

    @staticmethod
    async def send_email(
        email: str,
        subject: str,
        item: str,
    ) -> str:
        """
        Sends email.

        :param email: str
        :param subject: str
        :param item: str
        :return: Email verification code
        """
        code = "1234"
        if settings.mail_server:
            chars = string.digits
            code = "".join(secrets.choice(chars) for _ in range(4))
            message = MessageSchema(
                subject=f"Confirm {subject}",
                recipients=[email],
                html=f"<h1>Your {item}: <b>{code}</b></h1>",
                subtype="html",
            )
            fm = FastMail(settings.mail_conf)
            await fm.send_message(message)  # Relay exception
        return code


class AuthHandler:
    """Class for auth operations."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(
        self,
        password: str,
    ) -> str:
        """
        Get password hash.

        :param password: User password
        :return: Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        """
        Verify password.

        :param plain_password: Plain password
        :param hashed_password: Hashed password
        :return: Bool
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    async def registration_handler(
        self,
        email_object: UserEmailSchema,
        user_dao: UserDAO,
    ) -> None:
        """
        Registration handler.

        It creates hashed password for database storing

        :raises HTTPException: Bad registration
        :param email_object: UserEmailSchema
        :param user_dao: DAO of user model
        """
        if await user_dao.get_user(email=email_object.email):
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="EMAIL_ALREADY_REGISTERED",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="EMAIL_ALREADY_REGISTERED",
            )

        user_dict = email_object.dict()
        user_dict["code"] = await MailHandler.send_email(
            email=email_object.email,
            subject="registration",
            item="code",
        )
        await user_dao.create_user_model(user_dict)

    async def set_up_handler(
        self,
        set_up_object: UserSetUpSchema,
        user_dao: UserDAO,
    ) -> TokenSchema:
        """
        Set up handler.

        Finilize registration

        :raises HTTPException: Bad registration
        :param set_up_object: UserSetUpSchema
        :param user_dao: DAO of user model
        :return: Token
        """
        user = await user_dao.get_user(email=set_up_object.email)

        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="NO_SUCH_USER",
                    email=set_up_object.email,
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
        if user.set_up:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="USER_ALREADY_SET_UP",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="USER_ALREADY_SET_UP",
            )

        hashed_password = self.get_password_hash(set_up_object.password)
        set_up_object.password = hashed_password
        user_dict = set_up_object.dict()

        await user.update(**user_dict, set_up=True)

        return token_handler.get_tokens(identity=user.email)

    async def password_update_handler(
        self,
        password_object: UserPasswordUpdateSchema,
        user_email: str,
        user_dao: UserDAO,
    ) -> None:
        """
        Password update handler.

        :raises HTTPException: Bad registration
        :param password_object: UserPasswordUpdateSchema
        :param user_email: User email
        :param user_dao: DAO of user model
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        new_password = self.get_password_hash(password_object.new_password)

        if not self.verify_password(password_object.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_PASSWORD",
            )

        await user.update(password=new_password)

    async def passcode_handler(
        self,
        email: str,
        user_dao: UserDAO,
    ) -> None:
        """
        Passcode handler.

        Generates 4 int passcode and sends to user's email

        :raises HTTPException: Incorrect user
        :param email: str
        :param user_dao: DAO of user model
        """
        user = await user_dao.get_user(email=email)
        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="NO_SUCH_USER",
                    email=email,
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
                    email=email,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_VERIFIED",
            )
        code = await MailHandler.send_email(
            email=email,
            subject="password recover",
            item="temporary password",
        )
        await user.update(code=code)

    @staticmethod
    async def passcode_verify_handler(
        to_verify: CodeVerificationSchema,
        user_dao: UserDAO,
    ) -> bool:
        """
        Passcode verification handler.

        :raises HTTPException: Incorrect data
        :param to_verify: Data ti verify (email, passcode)
        :param user_dao: DAO of user model
        :return: True (verified) or raise error
        """
        user = await user_dao.get_user(email=to_verify.email)
        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="NO_SUCH_USER",
                    to_verify=to_verify.dict(),
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
                    to_verify=to_verify.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_NOT_VERIFIED",
            )
        if to_verify.code != user.code:
            await user.update(passcode="")
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INCORRECT_CODE",
                    to_verify=to_verify.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_CODE",
            )
        return True

    async def password_recover_handler(
        self,
        recover_data: UserPasswordRecoverSchema,
        user_dao: UserDAO,
    ) -> None:
        """
        Password recover handler.

        Updates user's password if passcode is correct

        :raises HTTPException: NO_SUCH_USER
        :param recover_data: UserPasswordRecoverSchema
        :param user_dao: DAO of user model
        """
        await self.passcode_verify_handler(
            CodeVerificationSchema(
                email=recover_data.email,
                code=recover_data.code,
            ),
            user_dao,
        )
        user = await user_dao.get_user(email=recover_data.email)
        if user is None:
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
        hashed_password = self.get_password_hash(recover_data.new_password)
        await user.update(code=None, password=hashed_password)

    @staticmethod
    async def confirmation_handler(
        verification_object: CodeVerificationSchema,
        user_dao: UserDAO,
    ) -> str:
        """
        Confirmation handler.

        Checks code and verifies user.

        :raises HTTPException: Bad confirmation
        :param verification_object: UserVerificationSchema
        :param user_dao: DAO of user model
        :return: Username
        """
        user = await user_dao.get_user(
            email=verification_object.email,
            select_related=True,
        )
        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INCORRECT_EMAIL",
                    verification_object=verification_object.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_EMAIL",
            )
        if user.verified:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="USER_ALREADY_VERIFIED",
                    verification_object=verification_object.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_ALREADY_VERIFIED",
            )
        if verification_object.code != user.code:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INCORRECT_CODE",
                    verification_object=verification_object.dict(),
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_CODE",
            )

        await user.clip_settings.update(
            **UserClipSettingsSchema().to_dict_model(),
        )
        await user.update(verified=True, code=None)

        return user.email

    async def resend_handler(
        self,
        email: str,
        user_dao: UserDAO,
    ) -> None:
        """
        Resend handler.

        Sends and updates email code.

        :raises HTTPException: Bad resend
        :param email: Email
        :param user_dao: DAO of user model
        """
        user = await user_dao.get_user(email=email)
        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INCORRECT_EMAIL",
                    email=email,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_EMAIL",
            )
        if user.verified:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="USER_ALREADY_VERIFIED",
                    email=email,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="USER_ALREADY_VERIFIED",
            )
        code = await MailHandler.send_email(
            email=email,
            subject="registration",
            item="code",
        )
        await user.update(code=code)

    async def login_handler(  # noqa: WPS238
        self,
        user_object: UserAuthorizationSchema,
        user_dao: UserDAO,
    ) -> TokenSchema:
        """
        Login handler.

        :raises HTTPException: Incorrect username or password
        :param user_object: User object
        :param user_dao: DAO of user model
        :return: Token
        """
        user = await user_dao.get_user(email=user_object.email)
        if not user:
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="NO_SUCH_USER",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
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
        hashed_password = user.dict()["password"]
        if not self.verify_password(user_object.password, hashed_password):
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="INCORRECT_PASSWORD",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INCORRECT_PASSWORD",
            )

        return token_handler.get_tokens(identity=user.email)

    async def logout_handler(
        self,
        token: str,
        token_dao: TokenDAO,
    ) -> None:
        """
        Logout handler.

        :raises HTTPException: Token blacklist check
        :param token: Token
        :param token_dao: DAO of token model
        """
        if await token_dao.check_token(token=token):
            bodylog.debug(
                LoggerMessages.exception(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="BLACKLIST_TOKEN",
                    token=token,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="BLACKLIST_TOKEN",
            )
        payload: Dict[str, Any] = TokenHandler.decode_token(  # type: ignore
            token,
            return_field="all",
        )
        await token_dao.add_token(
            token=token,
            exp=payload["exp"],
            iat=payload["iat"],
            scope=payload["scope"],
        )
