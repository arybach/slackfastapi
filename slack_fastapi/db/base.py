from ormar import ModelMeta

from slack_fastapi.db.config import database
from slack_fastapi.db.meta import meta


class BaseMeta(ModelMeta):
    """Base metadata for models."""

    database = database
    metadata = meta
