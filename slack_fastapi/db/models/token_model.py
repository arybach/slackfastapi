import ormar

from slack_fastapi.db.base import BaseMeta


class TokenModel(ormar.Model):
    """Revoked token's model."""

    class Meta(BaseMeta):
        tablename = "revoked_tokens"

    id: int = ormar.Integer(primary_key=True)
    token: str = ormar.String(max_length=256)  # noqa: WPS432
    exp: int = ormar.Integer()
    iat: int = ormar.Integer()
    scope: str = ormar.String(max_length=15)  # noqa: WPS432
