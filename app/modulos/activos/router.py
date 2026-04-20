from fastapi import APIRouter

from app.modulos.activos.routers import taller_router, vehiculo_router
from app.modulos.activos.routers.especialidad import router as especialidad_router
from app.modulos.activos.routers.historial_taller import router as historial_taller_router

router = APIRouter(prefix="/activos", tags=["Activos"])

router.include_router(taller_router)
router.include_router(vehiculo_router)
router.include_router(especialidad_router)
router.include_router(historial_taller_router)