from sqlalchemy.orm import Session
from typing import List, Optional

from app.modulos.activos.models.taller import Taller
from app.modulos.activos.models.especialidad import Especialidad
from app.modulos.activos.schemas.taller import TallerCreate, TallerUpdate


def crear_taller(db: Session, dueño_id: int, taller: TallerCreate, especialidades_ids: List[int] = None):
    from app.modulos.activos.services.especialidad import inicializar_especialidades
    
    inicializar_especialidades(db)
    
    db_taller = db.query(Taller).filter(Taller.dueño_id == dueño_id).first()
    if db_taller:
        return None

    db_taller = Taller(
        dueño_id=dueño_id,
        nombre=taller.nombre,
        ubicacion_lat=taller.ubicacion_lat,
        ubicacion_lng=taller.ubicacion_lng,
        telefono=taller.telefono,
        horario_atencion=taller.horario_atencion
    )
    
    if especialidades_ids:
        especialidades = db.query(Especialidad).filter(Especialidad.id.in_(especialidades_ids)).all()
        db_taller.especialidades = especialidades
    
    db.add(db_taller)
    db.commit()
    db.refresh(db_taller)
    return db_taller


def obtener_taller(db: Session, taller_id: int):
    return db.query(Taller).filter(Taller.id == taller_id).first()


def obtener_taller_por_dueño(db: Session, dueño_id: int):
    return db.query(Taller).filter(Taller.dueño_id == dueño_id).first()


def obtener_talleres(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Taller).offset(skip).limit(limit).all()


def obtener_talleres_por_especialidad(db: Session, especialidad_id: int):
    especialidad = db.query(Especialidad).filter(Especialidad.id == especialidad_id).first()
    if not especialidad:
        return []
    return list(especialidad.talleres)


def actualizar_taller(db: Session, taller_id: int, taller: TallerUpdate):
    db_taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not db_taller:
        return None

    update_data = taller.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_taller, key, value)

    db.commit()
    db.refresh(db_taller)
    return db_taller


def actualizar_especialidades_taller(db: Session, taller_id: int, especialidades_ids: List[int]):
    db_taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not db_taller:
        return None
    
    especialidades = db.query(Especialidad).filter(Especialidad.id.in_(especialidades_ids)).all()
    db_taller.especialidades = especialidades
    
    db.commit()
    db.refresh(db_taller)
    return db_taller


def eliminar_taller(db: Session, taller_id: int):
    db_taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not db_taller:
        return None

    db.delete(db_taller)
    db.commit()
    return db_taller