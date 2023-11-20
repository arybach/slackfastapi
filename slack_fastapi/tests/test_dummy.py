import uuid

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute  # Import APIRoute for debugging
from httpx import AsyncClient
from starlette import status

from slack_fastapi.db.dao.dummy_dao import DummyDAO


# Debugging helper function
def print_routes(app: FastAPI) -> None:
    """
    Print all routes registered in the FastAPI application.

    :param app: Instance of FastAPI application.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"Route: {route.name}, Path: {route.path}")  # noqa: WPS421


@pytest.mark.anyio
async def test_creation(
    fastapi_app: FastAPI,
    client: AsyncClient,
) -> None:
    """Tests dummy instance creation."""
    print_routes(fastapi_app)  # Debug: print all routes
    url = fastapi_app.url_path_for("create_dummy_model")
    print(f"URL for create_dummy_model: {url}")  # Debug: print the URL
    test_name = uuid.uuid4().hex
    response = await client.put(
        url,
        json={
            "name": test_name,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    dao = DummyDAO()
    instances = await dao.filter(name=test_name)
    assert instances[0].name == test_name


@pytest.mark.anyio
async def test_getting(
    fastapi_app: FastAPI,
    client: AsyncClient,
) -> None:
    """Tests dummy instance retrieval."""
    print_routes(fastapi_app)  # Debug: print all routes
    dao = DummyDAO()
    test_name = uuid.uuid4().hex
    await dao.create_dummy_model(name=test_name)
    url = fastapi_app.url_path_for("get_dummy_models")
    print(f"URL for get_dummy_models: {url}")  # Debug: print the URL
    response = await client.get(url)
    dummies = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(dummies) == 1
    assert dummies[0]["name"] == test_name
