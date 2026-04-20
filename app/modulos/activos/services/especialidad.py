from sqlalchemy.orm import Session
from typing import List, Optional

from app.modulos.activos.models.especialidad import Especialidad
from app.modulos.activos.schemas.especialidad import EspecialidadCreate


def crear_especialidad(db: Session, especialidad: EspecialidadCreate) -> Optional[Especialidad]:
    existente = db.query(Especialidad).filter(Especialidad.nombre == especialidad.nombre).first()
    if existente:
        return None
    
    db_especialidad = Especialidad(
        nombre=especialidad.nombre,
        descripcion=especialidad.descripcion
    )
    db.add(db_especialidad)
    db.commit()
    db.refresh(db_especialidad)
    return db_especialidad


def obtener_especialidades(db: Session) -> List[Especialidad]:
    return db.query(Especialidad).order_by(Especialidad.nombre).all()


def obtener_especialidad(db: Session, especialidad_id: int) -> Optional[Especialidad]:
    return db.query(Especialidad).filter(Especialidad.id == especialidad_id).first()


def eliminar_especialidad(db: Session, especialidad_id: int) -> Optional[Especialidad]:
    db_especialidad = db.query(Especialidad).filter(Especialidad.id == especialidad_id).first()
    if not db_especialidad:
        return None
    
    db_especialidad.talleres = []
    db.delete(db_especialidad)
    db.commit()
    return db_especialidad