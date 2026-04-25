from fastapi import APIRouter

from app.modulos.incidentes.routers import incidente, evidencia, historia_incidente

router = APIRouter(prefix="/incidentes", tags=["incidentes"])

router.include_router(incidente.router)
router.include_router(evidencia.router)
router.include_router(historia_incidente.router)