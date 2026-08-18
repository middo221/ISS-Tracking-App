from typing import Annotated

from fastapi import Depends, Request

from iss_tracker.config import Settings
from iss_tracker.services.iss_service import IssService


def get_iss_service(request: Request) -> IssService:
    service = getattr(request.app.state, "iss_service", None)
    if not isinstance(service, IssService):
        raise RuntimeError("The ISS service was not attached to the application")
    return service


def get_settings_from_app(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Settings were not attached to the application")
    return settings


IssServiceDep = Annotated[IssService, Depends(get_iss_service)]
SettingsDep = Annotated[Settings, Depends(get_settings_from_app)]
