import enum
import os
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from tempfile import gettempdir
from typing import List

from fastapi_mail import ConnectionConfig
from fastapi_mail.config import EmailStr
from pydantic import BaseSettings
from uvicorn.config import LOGGING_CONFIG
from yarl import URL

TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    host: str = "0.0.0.0"
    port: int = 8000
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = False

    # Current environment
    environment: str = "dev"

    @property
    def docs_title(self) -> str:
        title = "SlackCutter Backend"
        return "[{0}] {1}".format(
            self.environment.upper(),
            title,
        )

    @property
    def docs_description(self) -> str:
        return "".join(
            [
                "FastAPI backend for SlackCutter application\n\n",
                "Backend responsible: mats.tumblebuns@gmail.com\n\n",
            ],
        )

    log_level: LogLevel = LogLevel.INFO

    @property
    def log_config(self) -> LOGGING_CONFIG:
        """
        Assemble log config from settings.

        :return: Log config
        """
        log_config = LOGGING_CONFIG

        default_fmt = (
            "%(levelprefix)s | %(asctime)s.%(msecs)03d | %(message)s"  # noqa: WPS323
        )
        log_config["formatters"]["default"]["fmt"] = default_fmt
        log_config["formatters"]["default"][
            "datefmt"
        ] = "%Y-%m-%d %H:%M:%S"  # noqa: WPS323

        access_fmt = (
            "%(levelprefix)s | %(asctime)s.%(msecs)03d | %(message)s"  # noqa: WPS323
        )
        log_config["formatters"]["access"]["fmt"] = access_fmt
        log_config["formatters"]["access"][
            "datefmt"
        ] = "%Y-%m-%d %H:%M:%S"  # noqa: WPS323

        return log_config

    # Email settings
    mail_server: bool = False
    mail_host: str = "localhost"
    mail_port: int = 25
    mail_username: str = "root"
    mail_password: str = ""
    mail_from: EmailStr = "noreply@nutrients.tech"
    mail_from_name: str = ""
    mail_tls: bool = False
    mail_ssl: bool = False
    mail_use_credentials: bool = False
    mail_validate_certs: bool = False

    @property
    def mail_conf(self) -> ConnectionConfig:
        """
        Return connection config for mail agent.

        :return: Connection config
        """
        return ConnectionConfig(
            MAIL_SERVER=self.mail_host,
            MAIL_PORT=self.mail_port,
            MAIL_USERNAME=self.mail_username,
            MAIL_PASSWORD=self.mail_password,
            MAIL_FROM=self.mail_from,
            MAIL_FROM_NAME=self.mail_from_name,
            MAIL_TLS=self.mail_tls,
            MAIL_SSL=self.mail_ssl,
            USE_CREDENTIALS=self.mail_use_credentials,
            VALIDATE_CERTS=self.mail_validate_certs,
        )

    # S3 Bucket settings
    s3_region: str = "us-east-1"
    s3_bucket: str = "slackcutter-backend-dev"
    s3_prefix: str = "/prefix"
    s3_endpoint_url: str = "https://slackcutter-backend-dev.s3.amazonaws.com"
    s3_access_key: str = os.getenv("AWS_ACCESS_KEY_ID", "default_access_key")
    s3_secret_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "default_secret_key")

    # Temp files settings
    temp_dir: str = "temp/"

    # Logger settings
    logger_name_requests: str = "requests_logger"
    logger_name_bodies: str = "bodies_logger"
    logs_requests_path: str = "logs/requests/requests.log"
    logs_bodies_path: str = "logs/bodies/bodies.log"
    logs_time_units: str = "h"
    logs_interval: int = 24
    logs_backup_count: int = 100

    # Slackcutter
    trained_models: List[str] = [
        Path(path).name for path in glob("trained_models/*.joblib")
    ]

    # Variables for the database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "slack_fastapi"
    db_pass: str = "slack_fastapi"
    db_base: str = "slack_fastapi"
    db_echo: bool = False

    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.

        :return: database URL.
        """
        return URL.build(
            scheme="postgresql",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )

    # Variables for the JWT
    secret_key: str = "secret-string"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 6
    refresh_token_expire_hours: int = 24 * 14  # noqa: WPS432

    @property
    def jwt_creation_time(self) -> datetime:
        """:return: JWT Creation time."""
        return datetime.utcnow()

    @property
    def jwt_access_expires_at(self) -> datetime:
        """:return: JWT Access token expiration time."""
        return datetime.utcnow() + timedelta(
            days=0,
            hours=self.access_token_expire_hours,
        )

    @property
    def jwt_refresh_expires_at(self) -> datetime:
        """:return: JWT Refresh token expiration time."""
        return datetime.utcnow() + timedelta(
            days=0,
            hours=self.refresh_token_expire_hours,
        )

    class Config:
        env_file = ".env"
        env_prefix = "SLACK_FASTAPI_"
        env_file_encoding = "utf-8"


settings = Settings()
