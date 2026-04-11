from fastapi import APIRouter

from app.modulos.usuarios.routers import usuario_router, tecnico_router, notificacion_router

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

router.include_router(usuario_router)
router.include_router(tecnico_router)
router.include_router(notificacion_router)
