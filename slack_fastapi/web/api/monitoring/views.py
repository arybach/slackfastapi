from fastapi import FastAPI
from health_router import router as health_router  # Import the router
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Instrument the application
Instrumentator().instrument(app).expose(app)

# Include the health check router
app.include_router(health_router)
