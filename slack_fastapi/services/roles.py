from fastapi import HTTPException, status

from slack_fastapi.db.dao.videos_dao import VideoDAO


class BasicRole:
    """Basic role. Limited video upload capabilities."""

    days_to_check: int = 30
    video_limit_count: int = 5
    videos_per_day: int = 3

    def __str__(self) -> str:
        return "basic"

    async def restriction_check(self, user_id: int, video_dao: VideoDAO) -> None:
        """Checks if user is not available to upload videos.

        :raises exception: HTTPException: DAY_LIMIT_EXCEEDED, MONTH_LIMIT_EXCEEDED
        :param user_id: User ID.
        :param video_dao: Video DAO.
        """
        exception = await self.day_limit_exceeded(user_id, video_dao)
        if exception:
            raise exception

        exception = await self.month_limit_exceeded(user_id, video_dao)
        if exception:
            raise exception

    async def month_limit_exceeded(
        self,
        user_id: int,
        video_dao: VideoDAO,
    ) -> HTTPException | None:
        """Checks if user is not available to upload videos.

        :param user_id: User ID.
        :param video_dao: Video DAO.
        :return: HTTPException if user is not available to upload videos.
        """
        restricted = await video_dao.last_videos_within_days(
            user_id=user_id,
            days=self.days_to_check,
            amount=self.video_limit_count,
        )

        exception = None
        if restricted:
            exception = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MONTH_LIMIT_EXCEEDED",
            )

        return exception

    async def day_limit_exceeded(
        self,
        user_id: int,
        video_dao: VideoDAO,
    ) -> HTTPException | None:
        """Checks if user is not available to upload videos.

        :param user_id: User ID.
        :param video_dao: Video DAO.
        :return: HTTPException if user is not available to upload videos.
        """
        restricted = await video_dao.last_videos_within_days(
            user_id=user_id,
            days=1,
            amount=self.videos_per_day,
        )

        exception = None
        if restricted:
            exception = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="DAY_LIMIT_EXCEEDED",
            )

        return exception


class PremiumRole:
    """Premium role. Full video upload capabilities."""

    def __str__(self) -> str:
        return "premium"


class AdminRole:
    """Admin role. Can assign roles to users."""

    def __str__(self) -> str:
        return "admin"


class RoleManager:
    """Role manager. Manages roles."""

    basic: BasicRole = BasicRole()
    premium: PremiumRole = PremiumRole()
    admin: AdminRole = AdminRole()

    @staticmethod
    def is_basic(role: str) -> bool:
        return role == str(RoleManager.basic)

    @staticmethod
    def is_premium(role: str) -> bool:
        return role == str(RoleManager.premium)

    @staticmethod
    def is_admin(role: str) -> bool:
        return role == str(RoleManager.admin)
