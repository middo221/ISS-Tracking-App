from fastapi import APIRouter

from iss_tracker.api.v1 import health, iss

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(iss.router, prefix="/iss")
