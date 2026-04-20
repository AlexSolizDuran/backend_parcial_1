from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.modulos.activos.models.taller import Taller
from app.modulos.activos.schemas.taller import (
    TallerCreate, TallerUpdate, TallerResponse, 
    HistorialTallerResponse, HistorialTallerCreate,
    EspecialidadCreate, EspecialidadResponse
)
from app.modulos.activos.services import taller as taller_service
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.usuarios.models.usuario import Usuario

router = APIRouter(prefix="/taller", tags=["taller"])


@router.post("/", response_model=TallerResponse)
def crear_taller(
    taller: TallerCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden crear talleres")
    
    db_taller = taller_service.crear_taller(db, current_user.id, taller, taller.especialidades)
    if not db_taller:
        raise HTTPException(status_code=400, detail="Ya tienes un taller registrado")
    return db_taller


@router.get("/{taller_id}", response_model=TallerResponse)
def get_taller(taller_id: int, db: Session = Depends(get_db)):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    return db_taller


@router.get("/mi-taller/", response_model=TallerResponse)
def get_mi_taller(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    db_taller = taller_service.obtener_taller_por_dueño(db, current_user.id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="No tienes un taller registrado")
    return db_taller


@router.get("/", response_model=list[TallerResponse])
def get_talleres(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return taller_service.obtener_talleres(db, skip, limit)


@router.get("/especialidad/{especialidad_id}", response_model=list[TallerResponse])
def get_talleres_por_especialidad(especialidad_id: int, db: Session = Depends(get_db)):
    return taller_service.obtener_talleres_por_especialidad(db, especialidad_id)


@router.put("/{taller_id}", response_model=TallerResponse)
def update_taller(
    taller_id: int,
    taller: TallerUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este taller")
    
    return taller_service.actualizar_taller(db, taller_id, taller)


@router.put("/{taller_id}/especialidades", response_model=TallerResponse)
def update_especialidades_taller(
    taller_id: int,
    especialidades: List[int],
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este taller")
    
    return taller_service.actualizar_especialidades_taller(db, taller_id, especialidades)


@router.delete("/{taller_id}")
def delete_taller(
    taller_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este taller")
    
    taller_service.eliminar_taller(db, taller_id)
    return {"message": "Taller eliminado"}


@router.get("/{taller_id}/historial", response_model=list[HistorialTallerResponse])
def get_historial_taller(
    taller_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el historial")
    
    return taller_service.obtener_historial_taller(db, taller_id)


@router.post("/{taller_id}/historial", response_model=HistorialTallerResponse)
def create_historial_taller(
    taller_id: int,
    historial: HistorialTallerCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_taller = taller_service.obtener_taller(db, taller_id)
    if not db_taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if db_taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para agregar historial")
    
    return taller_service.crear_historial_taller(db, taller_id, historial)


router_esp = APIRouter(prefix="/especialidades", tags=["especialidades"])


@router_esp.get("/", response_model=list[EspecialidadResponse])
def get_especialidades(db: Session = Depends(get_db)):
    return taller_service.obtener_especialidades(db)


@router_esp.post("/", response_model=EspecialidadResponse)
def crear_especialidad(
    especialidad: EspecialidadCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden crear especialidades")
    
    db_especialidad = taller_service.crear_especialidad(db, especialidad)
    if not db_especialidad:
        raise HTTPException(status_code=400, detail="Ya existe una especialidad con ese nombre")
    return db_especialidad


@router_esp.delete("/{especialidad_id}")
def eliminar_especialidad(
    especialidad_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden eliminar especialidades")
    
    db_especialidad = taller_service.obtener_especialidad(db, especialidad_id)
    if not db_especialidad:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada")
    
    taller_service.eliminar_especialidad(db, especialidad_id)
    return {"message": "Especialidad eliminada"}