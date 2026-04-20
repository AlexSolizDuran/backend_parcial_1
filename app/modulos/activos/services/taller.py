from sqlalchemy.orm import Session
from typing import List, Optional

from app.modulos.activos.models.taller import Taller
from app.modulos.activos.models.especialidad import Especialidad
from app.modulos.activos.models.historial_taller import HistorialTaller
from app.modulos.activos.schemas.taller import TallerCreate, TallerUpdate, HistorialTallerCreate, EspecialidadCreate


ESPECIALIDADES_POR_DEFECTO = [
    "Frenos",
    "Motor",
    "Electricidad",
    "Chapa y Pintura",
    "Suspensión",
    "Diagnóstico Computarizado",
    "Cambio de Aceite",
    "Alineación y Balanceo",
]


def _crear_especialidades_default(db: Session):
    """Crea las especialidades por defecto si no existen"""
    existentes = db.query(Especialidad).all()
    if len(existentes) >= len(ESPECIALIDADES_POR_DEFECTO):
        return
    
    for nombre in ESPECIALIDADES_POR_DEFECTO:
        existente = db.query(Especialidad).filter(Especialidad.nombre == nombre).first()
        if not existente:
            db_especialidad = Especialidad(nombre=nombre)
            db.add(db_especialidad)
    db.commit()


def crear_taller(db: Session, dueño_id: int, taller: TallerCreate, especialidades_ids: List[int] = None):
    _crear_especialidades_default(db)
    
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


# Funciones para Especialidades

def crear_especialidad(db: Session, especialidad: EspecialidadCreate) -> Especialidad:
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


def eliminar_especialidad(db: Session, especialidad_id: int):
    db_especialidad = db.query(Especialidad).filter(Especialidad.id == especialidad_id).first()
    if not db_especialidad:
        return None
    
    db_especialidad.talleres = []
    db.delete(db_especialidad)
    db.commit()
    return db_especialidad


# Funciones para Historial Taller

def crear_historial_taller(db: Session, taller_id: int, historial: HistorialTallerCreate) -> HistorialTaller:
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo=historial.titulo,
        descripcion=historial.descripcion,
        tipo=historial.tipo
    )
    db.add(db_historial)
    db.commit()
    db.refresh(db_historial)
    return db_historial


def obtener_historial_taller(db: Session, taller_id: int) -> List[HistorialTaller]:
    return db.query(HistorialTaller).filter(
        HistorialTaller.taller_id == taller_id
    ).order_by(HistorialTaller.fecha.desc()).all()