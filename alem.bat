@echo off
IF "%~1"=="rev" (
    alembic revision --autogenerate -m %~2
    )
IF "%~1"=="up" (
    alembic upgrade head
    )
