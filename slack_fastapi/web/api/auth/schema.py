from pydantic import BaseModel, Field


class UserEmailSchema(BaseModel):
    """User email model."""

    email: str = Field(min_length=4, max_length=100)


class UserAuthorizationSchema(UserEmailSchema):
    """User authorization model."""

    password: str = Field(min_length=6, max_length=60)


class UserSetUpSchema(UserAuthorizationSchema):
    """User SetUp model."""

    first_name: str = Field(min_length=4, max_length=100)
    last_name: str = Field(min_length=4, max_length=100)


class CodeVerificationSchema(UserEmailSchema):
    """Codd authorization model."""

    code: str = Field(min_length=4, max_length=4)


class UserPasswordRecoverSchema(CodeVerificationSchema):
    """User password recover model."""

    new_password: str = Field(min_length=6, max_length=60)


class UserPasswordUpdateSchema(BaseModel):
    """User password update model."""

    password: str = Field(min_length=6, max_length=60)
    new_password: str = Field(min_length=6, max_length=60)


class TokenSchema(BaseModel):
    """Returns access and refresh tokens."""

    access_token: str
    refresh_token: str
