from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from typing import List, Optional
from app.modulos.asignacion.model import Asignacion, EstadoAsignacion, now_bolivia
from app.modulos.asignacion.schema import AsignacionCreate, AsignacionUpdate
from datetime import timedelta as td


def crear_asignacion(db: Session, incidente_id: int, taller_id: int, estado: EstadoAsignacion = EstadoAsignacion.pendiente, timeout_minutos: int = 2) -> Asignacion:
    db_asignacion = Asignacion(
        incidente_id=incidente_id,
        taller_id=taller_id,
        estado=estado,
        fecha_expiracion=now_bolivia() + td(minutes=timeout_minutos)
    )
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def crear_asignacion_from_schema(db: Session, asignacion: AsignacionCreate) -> Asignacion:
    db_asignacion = Asignacion(
        incidente_id=asignacion.incidente_id,
        taller_id=asignacion.taller_id,
        tecnico_id=asignacion.tecnico_id
    )
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def obtener_asignacion(db: Session, asignacion_id: int) -> Optional[Asignacion]:
    return db.query(Asignacion).filter(Asignacion.id == asignacion_id).first()


def obtener_asignaciones(db: Session, skip: int = 0, limit: int = 100) -> List[Asignacion]:
    return db.query(Asignacion).offset(skip).limit(limit).all()


def obtener_asignaciones_por_taller(db: Session, taller_id: int, skip: int = 0, limit: int = 100) -> List[Asignacion]:
    return db.query(Asignacion).filter(
        Asignacion.taller_id == taller_id
    ).offset(skip).limit(limit).all()


def obtener_asignaciones_por_incidente(db: Session, incidente_id: int) -> List[Asignacion]:
    return db.query(Asignacion).filter(Asignacion.incidente_id == incidente_id).all()


def actualizar_asignacion(db: Session, asignacion_id: int, asignacion_update: AsignacionUpdate) -> Optional[Asignacion]:
    db_asignacion = obtener_asignacion(db, asignacion_id)
    if not db_asignacion:
        return None
    
    update_data = asignacion_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_asignacion, field, value)
    
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def eliminar_asignacion(db: Session, asignacion_id: int) -> bool:
    db_asignacion = obtener_asignacion(db, asignacion_id)
    if not db_asignacion:
        return False
    
    db.delete(db_asignacion)
    db.commit()
    return True


def actualizar_asignacion_estado(db: Session, asignacion_id: int, estado: EstadoAsignacion, tecnico_id: Optional[int] = None) -> Optional[Asignacion]:
    db_asignacion = obtener_asignacion(db, asignacion_id)
    if not db_asignacion:
        return None
    
    db_asignacion.estado = estado
    if estado == EstadoAsignacion.aceptada:
        db_asignacion.fecha_aceptacion = now_bolivia()
    if tecnico_id:
        db_asignacion.tecnico_id = tecnico_id
    
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def aceptar_asignacion(db: Session, asignacion_id: int, tecnico_id: Optional[int] = None) -> Optional[Asignacion]:
    db_asignacion = obtener_asignacion(db, asignacion_id)
    if not db_asignacion:
        return None
    
    if db_asignacion.estado != EstadoAsignacion.pendiente:
        return None
    
    db_asignacion.estado = EstadoAsignacion.aceptada
    db_asignacion.fecha_aceptacion = now_bolivia()
    if tecnico_id:
        db_asignacion.tecnico_id = tecnico_id
    
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def crear_asignacion_aceptada(db: Session, incidente_id: int, taller_id: int, tecnico_id: int) -> Asignacion:
    """Crea asignación directamente con estado aceptada (para cuando taller acepta + selecciona técnico)"""
    db_asignacion = Asignacion(
        incidente_id=incidente_id,
        taller_id=taller_id,
        tecnico_id=tecnico_id,
        estado=EstadoAsignacion.aceptada,
        fecha_aceptacion=now_bolivia()
    )
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion