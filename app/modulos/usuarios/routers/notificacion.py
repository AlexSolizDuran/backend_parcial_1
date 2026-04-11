from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.usuarios.schemas.notificacion import NotificacionCreate, NotificacionResponse
from app.modulos.usuarios.services import notificacion as notificacion_service
from app.modulos.usuarios.routers.usuario import get_current_user

router = APIRouter(prefix="/notificacion")


@router.post("/", response_model=NotificacionResponse)
def crear_notificacion(notificacion: NotificacionCreate, db: Session = Depends(get_db)):
    return notificacion_service.crear_notificacion(db, notificacion)


@router.get("/{notificacion_id}", response_model=NotificacionResponse)
def get_notificacion(notificacion_id: int, db: Session = Depends(get_db)):
    db_notificacion = notificacion_service.obtener_notificacion(db, notificacion_id)
    if not db_notificacion:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    return db_notificacion


@router.get("/mis-notificaciones/", response_model=list[NotificacionResponse])
def get_mis_notificaciones(
    skip: int = 0,
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return notificacion_service.obtener_notificaciones_usuario(db, current_user.id, skip, limit)


@router.put("/{notificacion_id}/leer", response_model=NotificacionResponse)
def marcar_leido(notificacion_id: int, db: Session = Depends(get_db)):
    db_notificacion = notificacion_service.marcar_como_leido(db, notificacion_id)
    if not db_notificacion:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    return db_notificacion


@router.delete("/{notificacion_id}")
def delete_notificacion(notificacion_id: int, db: Session = Depends(get_db)):
    db_notificacion = notificacion_service.eliminar_notificacion(db, notificacion_id)
    if not db_notificacion:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    return {"message": "Notificacion eliminada"}
