from slack_fastapi.db.dao.users_dao import UserDAO
from slack_fastapi.logger.services import LoggerMethods
from slack_fastapi.web.api.auth.helpers import general_access_check
from slack_fastapi.web.api.user.schema import UserClipSettingsSchema, UserSchema

bodylog = LoggerMethods.get_bodies_logger()


class UserHandler:
    """Class for user operations."""

    @staticmethod
    async def get_user(
        user_email: str,
        user_dao: UserDAO,
    ) -> UserSchema:
        """
        Returns UserSchema.

        :param user_email: User's email
        :param user_dao: UserDAO
        :return: UserSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email),
        )

        return UserSchema(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=user.role,
            verified=user.verified,
            created=user.created,
        )

    @staticmethod
    async def get_clip_settings(
        user_email: str,
        user_dao: UserDAO,
    ) -> UserClipSettingsSchema:
        """
        Returns UserClipSettingsSchema.

        :param user_email: User's email
        :param user_dao: UserDAO
        :return: UserSchema
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email, select_related=True),
        )

        return UserClipSettingsSchema(
            trained_mode=user.clip_settings.trained_model,
            max_seconds_lenght=user.clip_settings.max_seconds_lenght,
            model_threshold=user.clip_settings.model_threshold,
            median_hit_modificator=user.clip_settings.median_hit_modificator,
            noice_threshold=list(
                map(int, user.clip_settings.noice_threshold.split(",")),
            ),
            audio_threshold=list(
                map(int, user.clip_settings.audio_threshold.split(",")),
            ),
            crop_interval=list(map(int, user.clip_settings.crop_interval.split(","))),
            sound_check=user.clip_settings.sound_check,
        )

    @staticmethod
    async def update_clip_settings(
        settings: UserClipSettingsSchema,
        user_email: str,
        user_dao: UserDAO,
    ) -> None:
        """
        Updates UserClipSettingsSchema.

        :param settings: UserClipSettingsSchema
        :param user_email: User's email
        :param user_dao: UserDAO
        """
        user = general_access_check(
            await user_dao.get_user(email=user_email, select_related=True),
        )

        changes = settings.to_dict_model()

        await user.clip_settings.update(**changes)
