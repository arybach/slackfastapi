# health_router.py
from typing import Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, str]:
    """
    Checks the health of the project.

    :returns:
        Dict[str, str]: A dictionary with the health status of the project.
        The dictionary contains:
        - 'status': A string indicating the health status ('healthy').
    """
    return {"status": "healthy"}
