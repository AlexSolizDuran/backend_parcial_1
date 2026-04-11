from fastapi import APIRouter

from app.modulos.activos.routers import taller_router, vehiculo_router

router = APIRouter(prefix="/activos", tags=["Activos"])

router.include_router(taller_router)
router.include_router(vehiculo_router)
