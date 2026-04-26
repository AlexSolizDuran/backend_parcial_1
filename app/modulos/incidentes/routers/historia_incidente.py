from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.modulos.incidentes.services.historia_incidente import crear_historia_incidente, obtener_historia_incidente
from app.modulos.incidentes.schemas.historia_incidente import HistoriaIncidenteCreate, HistoriaIncidenteResponse
from app.modulos.incidentes.services.incidente import obtener_incidente
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.asignacion.model import Asignacion
from app.core.security import get_current_user

router = APIRouter(tags=["historia-incidente"])


def verificar_permiso_historia(incidente, current_user, db):
    """Verifica si el usuario tiene permiso para ver/modificar la historia del incidente"""
    # Cliente propietario
    if current_user.id == incidente.cliente_id:
        return True
    # Dueño del taller
    if current_user.rol.value == "dueno":
        return True
    # Técnico asignado al incidente
    from app.modulos.usuarios.models.tecnico import Tecnico
    db_tecnico = db.query(Tecnico).filter(Tecnico.usuario_id == current_user.id).first()
    if db_tecnico:
        asignacion_tecnico = db.query(Asignacion).filter(
            Asignacion.incidente_id == incidente.id,
            Asignacion.tecnico_id == db_tecnico.id
        ).first()
        if asignacion_tecnico:
            return True
    return False


@router.get("/{incidente_id}/historia", response_model=List[HistoriaIncidenteResponse])
def obtener_historia_incidente_endpoint(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Get history timeline for an incident"""
    incidente = obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if not verificar_permiso_historia(incidente, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver la historia de este incidente"
        )
    
    return obtener_historia_incidente(db, incidente_id)


@router.post("/{incidente_id}/historia", response_model=HistoriaIncidenteResponse)
def crear_historia_incidente_endpoint(
    incidente_id: int,
    historia: HistoriaIncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Create a new history entry for an incident"""
    incidente = obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if not verificar_permiso_historia(incidente, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para agregar historia a este incidente"
        )
    
    return crear_historia_incidente(db, incidente_id, historia)