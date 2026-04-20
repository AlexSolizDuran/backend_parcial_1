from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.modulos.activos.models.historial_taller import HistorialTaller
from app.modulos.activos.schemas.historial_taller import HistorialTallerCreate


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


def crear_historial_incidente_llegada(db: Session, taller_id: int, incidente_id: int, distancia: float):
    """Crea historial cuando llega un incidente cercano"""
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo="Nuevo incidente cercano",
        descripcion=f"Se detectó un nuevo incidente a {distancia}km de distancia",
        tipo="incidente_llegada"
    )
    db.add(db_historial)
    db.commit()


def crear_historial_incidente_aceptado(db: Session, taller_id: int, incidente_id: int):
    """Crea historial cuando se acepta un incidente"""
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo="Incidente asignado",
        descripcion=f"Se ha aceptado el incidente #{incidente_id}",
        tipo="incidente_aceptado"
    )
    db.add(db_historial)
    db.commit()


def crear_historial_incidente_rechazado(db: Session, taller_id: int, incidente_id: int, motivo: str):
    """Crea historial cuando se rechaza un incidente"""
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo="Incidente rechazado",
        descripcion=f"Se ha rechazado el incidente #{incidente_id}. Motivo: {motivo}",
        tipo="incidente_rechazado"
    )
    db.add(db_historial)
    db.commit()


def crear_historial_tecnico_termino(db: Session, taller_id: int, tecnico_nombre: str, incidente_id: int):
    """Crea historial cuando un técnico termina su trabajo"""
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo="Trabajo completado",
        descripcion=f"El técnico {tecnico_nombre} ha completado el trabajo del incidente #{incidente_id}",
        tipo="tecnico_termino"
    )
    db.add(db_historial)
    db.commit()