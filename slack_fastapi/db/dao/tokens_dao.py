import ormar

from slack_fastapi.db.models.token_model import TokenModel


class TokenDAO:
    """Class for accessing tokens table."""

    @staticmethod
    async def add_token(
        token: str,
        exp: int,
        iat: int,
        scope: str,
    ) -> None:
        """
        Add token to revoked token's table.

        :param token: Token
        :param exp: Expiration time
        :param iat: Creation time
        :param scope: Scope
        """
        await TokenModel.objects.create(
            token=token,
            exp=exp,
            iat=iat,
            scope=scope,
        )

    @staticmethod
    async def check_token(
        token: str,
    ) -> bool:
        """
        Check token in revoked token's table.

        :param token: Token
        :return: List
        """
        try:
            await TokenModel.objects.filter(TokenModel.token == token).first()
        except ormar.exceptions.NoMatch:
            return False
        return True

    @staticmethod
    async def delete_token(
        token: str,
    ) -> None:
        """
        Delete token from revoked token's table.

        :param token: Token
        """
        await TokenModel.objects.delete(TokenModel.token == token)
