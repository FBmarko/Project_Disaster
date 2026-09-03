from fastapi import APIRouter

from app.api.v1.endpoints import earthquake_hazards, earthquakes, fault_lines, health

v1_router = APIRouter()
v1_router.include_router(health.router, tags=["Health"])
v1_router.include_router(
    fault_lines.router, prefix="/fault-lines", tags=["Fault Lines"]
)
v1_router.include_router(
    earthquakes.router, prefix="/earthquakes", tags=["Earthquakes"]
)
v1_router.include_router(
    earthquake_hazards.router,
    prefix="/earthquake-hazards",
    tags=["Earthquake Hazards"],
)
