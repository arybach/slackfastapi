from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """Default schema for success response."""

    msg: str = Field(example="Everything OK")


class IdSchema(BaseModel):
    """Default schema for id response."""

    id: int = Field(ge=1, default=None, example=1)


class IdStrictSchema(BaseModel):
    """Default schema for required id request."""

    id: int = Field(ge=1, example=1)
