from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.usuarios.schemas.tecnico import TecnicoResponse, TecnicoCreate
from app.modulos.usuarios.services import tecnico as tecnico_service
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.activos.models.taller import Taller

router = APIRouter(prefix="/tecnico")

class tecnicoConTaller(BaseModel):
    disponible: bool = True
    usuario_id: int

@router.post("/", response_model=TecnicoResponse)
def crear_tecnico(
    tecnico: tecnicoConTaller,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueño pueden crear técnicos")
    
    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        raise HTTPException(status_code=400, detail="No tienes un taller registrado")
    
    if not tecnico.usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")
    
    db_tecnico = tecnico_service.asignar_taller(db, tecnico.usuario_id, taller.id, tecnico.disponible)
    if not db_tecnico:
        db_tecnico = tecnico_service.crear_tecnico_por_usuario_id(db, tecnico.usuario_id, taller.id, tecnico.disponible)
    return db_tecnico

@router.post("/registrar", response_model=TecnicoResponse)
def registrar_tecnico(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "tecnico":
        raise HTTPException(status_code=403, detail="Solo usuarios con rol tecnico pueden registrarse")
    
    db_tecnico = tecnico_service.crear_tecnico(db, current_user.id)
    if not db_tecnico:
        raise HTTPException(status_code=400, detail="Ya existe un tecnico para este usuario")
    return db_tecnico


@router.get("/{tecnico_id}", response_model=TecnicoResponse)
def get_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    db_tecnico = tecnico_service.obtener_tecnico(db, tecnico_id)
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")
    return db_tecnico


@router.get("/", response_model=list[TecnicoResponse])
def get_tecnicos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden ver técnicos")
    
    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        return []
    
    return tecnico_service.obtener_tecnicos_por_taller(db, taller.id)


@router.get("/disponibles/", response_model=list[TecnicoResponse])
def get_tecnicos_disponibles(taller_id: int = None, db: Session = Depends(get_db)):
    return tecnico_service.obtener_tecnicos_disponibles(db, taller_id)


@router.put("/{tecnico_id}/disponibilidad", response_model=TecnicoResponse)
def update_disponibilidad(tecnico_id: int, disponible: bool, db: Session = Depends(get_db)):
    db_tecnico = tecnico_service.actualizar_disponibilidad(db, tecnico_id, disponible)
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")
    return db_tecnico


@router.delete("/{tecnico_id}")
def delete_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    db_tecnico = tecnico_service.eliminar_tecnico(db, tecnico_id)
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")
    return {"message": "Tecnico eliminado"}
