"""Sonde de vivacité ([SANTE]) : route publique, sans donnée."""

from fastapi import APIRouter
from pydantic import BaseModel

HEALTH_STATUS_OK = "ok"

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


# [PERMISSIONS] : route publique, sans donnée, utilisée comme sonde de vivacité ([SANTE]).
@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status=HEALTH_STATUS_OK)
