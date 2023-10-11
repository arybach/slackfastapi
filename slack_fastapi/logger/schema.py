from pydantic import BaseModel

from slack_fastapi.settings import settings


class LoggerRequestsModel(BaseModel):
    """Logging configuration to be set for the server."""

    LOGGER_NAME: str = settings.logger_name_requests
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"  # noqa: WPS323
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",  # noqa: WPS323
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "rotaiton": {
            "formatter": "default",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": settings.logs_time_units,
            "interval": settings.logs_interval,
            "backupCount": settings.logs_backup_count,
            "filename": settings.logs_requests_path,
            "encoding": "utf-8",
        },
    }
    loggers = {
        settings.logger_name_requests: {
            "handlers": ["default", "rotaiton"],
            "level": LOG_LEVEL,
        },
    }


class LoggerBodiesModel(BaseModel):
    """Logging configuration to be set for the server."""

    LOGGER_NAME: str = settings.logger_name_bodies
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | [%(module)s:%(funcName)s:%(lineno)-4d] %(message)s | %(pathname)s LINE: %(lineno)-4d"  # noqa: E501, WPS323
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",  # noqa: WPS323
        },
    }
    handlers = {
        "rotaiton": {
            "formatter": "default",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": settings.logs_time_units,
            "interval": settings.logs_interval,
            "backupCount": settings.logs_backup_count,
            "filename": settings.logs_bodies_path,
            "encoding": "utf-8",
        },
    }
    loggers = {
        settings.logger_name_bodies: {
            "handlers": ["rotaiton"],
            "level": LOG_LEVEL,
        },
    }
