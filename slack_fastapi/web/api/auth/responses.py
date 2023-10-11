from typing import Any, Dict


class AuthResponses:
    """Class for auth responses."""

    registration_responses: Dict[int | str, Any] = {
        400: {
            "description": "Registration failure",
            "content": {
                "application/json": {
                    "examples": {
                        "Registered email": {
                            "summary": "Registered email",
                            "value": {"detail": "EMAIL_ALREADY_REGISTERED"},
                        },
                    },
                },
            },
        },
    }

    passcode_responses: Dict[int | str, Any] = {
        404: {
            "description": "Registration failure",
            "content": {
                "application/json": {
                    "examples": {
                        "No such user": {
                            "summary": "No such user",
                            "value": {"detail": "NO_SUCH_USER"},
                        },
                    },
                },
            },
        },
        401: {
            "description": "Registration failure",
            "content": {
                "application/json": {
                    "examples": {
                        "User not verified": {
                            "summary": "User not verified",
                            "value": {"detail": "USER_NOT_VERIFIED"},
                        },
                    },
                },
            },
        },
    }

    password_recover_responses: Dict[int | str, Any] = {
        404: {
            "description": "Registration failure",
            "content": {
                "application/json": {
                    "examples": {
                        "No such user": {
                            "summary": "No such user",
                            "value": {"detail": "NO_SUCH_USER"},
                        },
                    },
                },
            },
        },
        401: {
            "description": "Registration failure",
            "content": {
                "application/json": {
                    "examples": {
                        "User not verified": {
                            "summary": "User not verified",
                            "value": {"detail": "USER_NOT_VERIFIED"},
                        },
                        "Incorrect code": {
                            "summary": "Incorrect code",
                            "value": {"detail": "INCORRECT_CODE"},
                        },
                    },
                },
            },
        },
    }

    login_responses: Dict[int | str, Any] = {
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "examples": {
                        "No such user": {
                            "summary": "No such user",
                            "value": {"detail": "NO_SUCH_USER"},
                        },
                        "User not verified": {
                            "summary": "User not verified",
                            "value": {"detail": "USER_NOT_VERIFIED"},
                        },
                        "Incorrect password": {
                            "summary": "Incorrect password",
                            "value": {"detail": "INCORRECT_PASSWORD"},
                        },
                    },
                },
            },
        },
    }

    confirmation_responses: Dict[int | str, Any] = {
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "examples": {
                        "Incorrect email": {
                            "summary": "Incorrect email",
                            "value": {"detail": "INCORRECT_EMAIL"},
                        },
                        "User already verified": {
                            "summary": "User already verified",
                            "value": {"detail": "USER_ALREADY_VERIFIED"},
                        },
                        "Incorrect code": {
                            "summary": "Incorrect code",
                            "value": {"detail": "INCORRECT_CODE"},
                        },
                    },
                },
            },
        },
    }

    resend_responses: Dict[int | str, Any] = {
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "examples": {
                        "Incorrect email": {
                            "summary": "Incorrect email",
                            "value": {"detail": "INCORRECT_EMAIL"},
                        },
                        "User already verified": {
                            "summary": "User already verified",
                            "value": {"detail": "USER_ALREADY_VERIFIED"},
                        },
                    },
                },
            },
        },
    }

    jwt_responses: Dict[int | str, Any] = {
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "examples": {
                        "Token in blacklist": {
                            "summary": "Token in blacklist",
                            "value": {"detail": "BLACKLIST_TOKEN"},
                        },
                        "Token expired": {
                            "summary": "Token expired",
                            "value": {"detail": "TOKEN_EXPIRED"},
                        },
                        "Invalid token": {
                            "summary": "Invalid token",
                            "value": {"detail": "INVALID_TOKEN"},
                        },
                    },
                },
            },
        },
    }
