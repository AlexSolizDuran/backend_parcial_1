from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.modulos.activos.services.taller import obtener_taller
from app.modulos.activos.services.historial_taller import crear_historial_taller, obtener_historial_taller
from app.modulos.activos.schemas.historial_taller import HistorialTallerCreate, HistorialTallerResponse
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.usuarios.models.usuario import Usuario

router = APIRouter(prefix="/taller", tags=["historial-taller"])


@router.get("/{taller_id}/historial", response_model=List[HistorialTallerResponse])
def get_historial_taller_endpoint(
    taller_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el historial")
    
    return obtener_historial_taller(db, taller_id)


@router.post("/{taller_id}/historial", response_model=HistorialTallerResponse)
def crear_historial_taller_endpoint(
    taller_id: int,
    historial: HistorialTallerCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para agregar historial")
    
    return crear_historial_taller(db, taller_id, historial)