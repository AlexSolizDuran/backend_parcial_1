from sqlalchemy.orm import Session
from typing import List, Optional

from app.modulos.activos.models.especialidad import Especialidad
from app.modulos.activos.schemas.especialidad import EspecialidadCreate


ESPECIALIDADES_POR_DEFECTO = [
    {"nombre": "mecanica", "descripcion": "Reparaciones mecánicas generales"},
    {"nombre": "chapa", "descripcion": "Reparación de carrocería y pintura"},
    {"nombre": "electricidad", "descripcion": "Sistema eléctrico y electrónica vehicular"},
    {"nombre": "frenos", "descripcion": "Sistema de frenado"},
    {"nombre": "suspension", "descripcion": "Sistema de suspensión y dirección"},
    {"nombre": "motor", "descripcion": "Reparación de motor"},
    {"nombre": "transmision", "descripcion": "Caja de cambios y transmisión"},
    {"nombre": "aire_acondicionado", "descripcion": "Sistema de climatización"},
    {"nombre": "vidrios", "descripcion": "Reparación y reemplazo de vidrios"},
    {"nombre": "neumaticos", "descripcion": "Cambio y reparación de neumáticos"},
]


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


def inicializar_especialidades(db: Session):
    """Crea las especialidades por defecto si no existen"""
    for esp in ESPECIALIDADES_POR_DEFECTO:
        existente = db.query(Especialidad).filter(Especialidad.nombre == esp["nombre"]).first()
        if not existente:
            db_esp = Especialidad(nombre=esp["nombre"], descripcion=esp["descripcion"])
            db.add(db_esp)
    db.commit()


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