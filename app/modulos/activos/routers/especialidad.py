from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.modulos.activos.services.especialidad import crear_especialidad, obtener_especialidades, eliminar_especialidad, obtener_especialidad
from app.modulos.activos.schemas.especialidad import EspecialidadCreate, EspecialidadResponse
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.usuarios.models.usuario import Usuario

router = APIRouter(prefix="/especialidades", tags=["especialidades"])


@router.get("/", response_model=list[EspecialidadResponse])
def get_especialidades(db: Session = Depends(get_db)):
    return obtener_especialidades(db)


@router.post("/", response_model=EspecialidadResponse)
def crear_especialidad_endpoint(
    especialidad: EspecialidadCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden crear especialidades")
    
    db_especialidad = crear_especialidad(db, especialidad)
    if not db_especialidad:
        raise HTTPException(status_code=400, detail="Ya existe una especialidad con ese nombre")
    return db_especialidad


@router.delete("/{especialidad_id}")
def eliminar_especialidad_endpoint(
    especialidad_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden eliminar especialidades")
    
    db_especialidad = obtener_especialidad(db, especialidad_id)
    if not db_especialidad:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada")
    
    eliminar_especialidad(db, especialidad_id)
    return {"message": "Especialidad eliminada"}