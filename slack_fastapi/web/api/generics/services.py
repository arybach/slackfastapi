import hashlib
from time import time
from typing import Any

from fastapi.responses import JSONResponse

from slack_fastapi.web.api.generics.schemas import SuccessResponse


class ResponseHandler:
    """Class for JSON response operations."""

    @staticmethod
    def response_handler(**kwargs: dict[str, Any]) -> JSONResponse:
        """
        Response messages handler.

        :param kwargs: Arguments for response
        :return: JSON Response
        """
        return JSONResponse(
            content=kwargs,
        )

    @staticmethod
    def success_response(msg: str) -> SuccessResponse:
        """
        Default handler for success response.

        :param msg: Message for response
        :return: Success response
        """
        return SuccessResponse(msg=msg)


class Generics:
    """Generic functions."""

    @staticmethod
    def string2md5(string: str) -> str:
        """
        Converts string to md5 string.

        :param string: Some string
        :return: md5 string made up from input
        """
        return hashlib.md5(string.encode("utf-8")).hexdigest()  # noqa: S324

    @staticmethod
    def bytes2md5(data: bytes) -> str:
        """
        Returns md5 string out of data bytes.

        :param data: bytes
        :return: md5 string made up from input
        """
        return hashlib.md5(data).hexdigest()  # noqa: S324

    @staticmethod
    def get_unixstring() -> str:
        """
        Returns current unix time string representation.

        :return: unix time string
        """
        return str(int(time() * 10000000))  # noqa: WPS432
