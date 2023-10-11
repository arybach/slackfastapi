from fastapi.routing import APIRouter

from slack_fastapi.web.api import auth, monitoring, user, video

api_router = APIRouter()
api_router.include_router(monitoring.router, tags=["System"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authorization"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(video.router, tags=["Video"])
