from databases import Database

from slack_fastapi.settings import settings

database = Database(str(settings.db_url))
