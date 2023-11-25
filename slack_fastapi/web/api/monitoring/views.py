from typing import Dict

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Instrument the application
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health_check() -> Dict[str, str]:
    """
    Checks the health of the project.

    Returns:
        Dict[str, str]: A dictionary with the health status of the project.
        The dictionary contains:
        - 'status': A string indicating the health status ('healthy').
    """
    return {"status": "healthy"}
