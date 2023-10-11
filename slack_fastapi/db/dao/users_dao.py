import datetime
from typing import Any, Dict

from ormar.exceptions import NoMatch

from slack_fastapi.db.models.user_model import UserClipSettingsModel, UserModel


class UserDAO:
    """Class for accessing users table."""

    @staticmethod
    async def create_user_model(
        user_object: Dict[str, Any],
    ) -> None:
        """
        Add single user to session.

        :param user_object: User object
        """
        clip_settings = await UserClipSettingsModel().save()
        verified = False
        await UserModel.objects.create(
            email=user_object["email"],
            password=user_object.get("password"),
            verified=verified,
            code=user_object["code"],
            clip_settings=clip_settings,
            created=datetime.datetime.now(),
        )

    @staticmethod
    async def get_user(
        email: str,
        select_related: bool = False,
    ) -> UserModel | None:
        """
        Get user by email.

        :param email: Email
        :param select_related: Select UserClipSettingsModel if needed
        :return: UserModel
        """
        if select_related:
            query = UserModel.objects.filter(UserModel.email == email).select_related(
                UserModel.clip_settings,  # type: ignore
            )
        else:
            query = UserModel.objects.filter(UserModel.email == email)
        try:
            return await query.first()
        except NoMatch:
            return None

    @staticmethod
    async def get_user_settings(
        foreign_id: int,
    ) -> UserClipSettingsModel | None:
        """
        Get user settings by foreign id.

        :param foreign_id: Foreign id
        :return: User settings or None
        """
        query = UserClipSettingsModel.objects.filter(
            UserClipSettingsModel.id == foreign_id,
        )
        try:
            return await query.first()
        except NoMatch:
            return None
