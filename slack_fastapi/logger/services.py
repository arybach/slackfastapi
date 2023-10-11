import logging
from logging.config import dictConfig
from pathlib import Path
from typing import Any

from fastapi import Request
from starlette.concurrency import iterate_in_threadpool

from slack_fastapi.logger.schema import LoggerBodiesModel, LoggerRequestsModel
from slack_fastapi.settings import settings


class LoggerMessages:
    """Class for accessing logging messages ."""

    @staticmethod
    def middleware_request(request: Request, response: Any) -> str:
        """
        Handler for generating request logging message.

        :param request: Request.
        :param response: Response.
        :return: Formated string made of request's method, url.scheme, status_code, url.path.  # noqa: E501
        """
        return f"[{request.method}] [{request.url.scheme}: {response.status_code}] [{request.url.path}]"  # noqa: E501, WPS221, WPS237

    @staticmethod
    def middleware_requestbody(request_body: str) -> str:
        """
        Handler for generating request's body logging message.

        :param request_body: Request's body.
        :return: Formated string containing requst's body information.
        """
        return f"\nRequestBody:\n{request_body}\n"

    @staticmethod
    def middleware_responsebody(response_body: Any) -> str:
        """
        Handler for generating response body logging message.

        :param response_body: Response body.
        :return: Formated string containing response body information.
        """
        return f"\nResponseBody:\n{response_body[0].decode()}\n"  # noqa: WPS237

    @staticmethod
    def exception(status_code: int, detail: str, **kwargs) -> str:  # type: ignore
        """
        Handler for generating exception body logging message.

        :param status_code: HTTP status code.
        :param detail: Detail about the error.
        :param **kwargs: Additional input values.
        :return: Formated string containing exception body information.
        """
        arguments = []

        for key, value in kwargs.items():
            arguments.append(f"{key}: {value}")

        arguments_str = " | ".join(arguments)

        return f"[{arguments_str}] Status code: {status_code}, detail: {detail}"


class LoggerMethods:
    """Class for accessing logger objects."""

    @staticmethod
    def get_requests_logger() -> logging.Logger:
        """
        Handler for accessing requests logger.

        :return: Requests logger object.
        """
        directory_path = "/".join(settings.logs_requests_path.split("/")[:-1])
        Path(directory_path).mkdir(
            parents=True,
            exist_ok=True,
        )
        dictConfig(LoggerRequestsModel().dict())
        return logging.getLogger(settings.logger_name_requests)

    @staticmethod
    def get_bodies_logger() -> logging.Logger:
        """
        Handler for accessing bodies logger.

        :return: Bodies logger object.
        """
        directory_path = "/".join(settings.logs_bodies_path.split("/")[:-1])
        Path(directory_path).mkdir(
            parents=True,
            exist_ok=True,
        )
        dictConfig(LoggerBodiesModel().dict())
        return logging.getLogger(settings.logger_name_bodies)


class LoggerMiddleware:
    """Middleware for logging incoming requests."""

    requestlog = LoggerMethods.get_requests_logger()
    bodylog = LoggerMethods.get_bodies_logger()

    FORBIDDEN_403 = 403  # noqa: WPS114
    OK_200 = 200  # noqa: WPS114
    UNPROCESSABLE_ENTITY_422 = 422  # noqa: WPS114

    API_LOGIN = "/api/auth/login"
    API_REGISTER = "/api/auth/register"

    BLACK_APIS = [
        "api/video/download",
        "api/video/clip/download",
    ]

    async def set_body(self, request: Request, body: bytes) -> None:
        """
        Sets new body for request so the previous one could be extracted.

        :param request: Request.
        :param body: Request's body.
        """

        async def receive() -> dict[str, Any]:  # noqa: WPS430
            return {"type": "http.request", "body": body}

        request._receive = receive  # noqa: WPS437

    async def get_body(self, request: Request) -> bytes:
        """
        Extracts body from the request.

        :param request: Request.
        :return: Request's body encoded in bytes.
        """
        body = await request.body()
        await self.set_body(request, body)
        return body

    async def log_response_body(self, response: Any) -> None:
        """
        Used to safely log response body.

        :param response: Response.
        """
        if response.status_code != self.UNPROCESSABLE_ENTITY_422:
            return

        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))

        self.bodylog.warning(
            LoggerMessages.middleware_responsebody(response_body=response_body),
        )

    async def log_request_body(
        self,
        response: Any,
        request: Request,
        request_body: str,
    ) -> None:
        """
        Used to safely log request body.

        :param response: Response.
        :param request: Request.
        :param request_body: Request's body.
        """
        if response.status_code in {  # noqa: WPS337
            self.FORBIDDEN_403,
            self.OK_200,
        }:
            return

        self.requestlog.warning(
            LoggerMessages.middleware_request(request=request, response=response),
        )

        if request.url.path not in {self.API_LOGIN, self.API_REGISTER} and request_body:
            self.bodylog.warning(
                LoggerMessages.middleware_requestbody(request_body=request_body),
            )

    async def process_request(  # noqa: WPS217
        self,
        request: Request,
        call_next: Any,
    ) -> Any:
        """
        Middleware logic. Extract request information before response and logs it after.

        :param request: Request.
        :param call_next: Some iternal logic function.
        :return: Response.
        """
        if request.scope.get("path") not in self.BLACK_APIS:
            request_body = ""
            if request.headers.get("content-type"):
                await self.set_body(request, await request.body())
                request_type = request.headers["content-type"].split(";")[0]
                if request_type == "application/json":
                    request_body = (await self.get_body(request)).decode("utf-8")
                elif request_type == "multipart/form-data":
                    request_body = (
                        (await self.get_body(request))
                        .split(b"filename=")[0]
                        .decode("utf-8")
                    )

        response = await call_next(request)

        await self.log_response_body(response=response)
        await self.log_request_body(
            response=response,
            request=request,
            request_body=request_body,
        )

        return response
