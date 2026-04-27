from sqlalchemy.orm import Session
from typing import List, Optional
from app.modulos.finanzas.model import Pago
from app.modulos.finanzas.schema import PagoCreate, PagoUpdate
from app.modulos.asignacion.model import Asignacion


def crear_pago(db: Session, pago: PagoCreate) -> Pago:
    db_pago = Pago(
        monto_total=pago.monto_total,
        monto_comision=pago.monto_comision,
        asignacion_id=pago.asignacion_id,
        estado=False
    )
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago


def obtener_pago(db: Session, pago_id: int) -> Optional[Pago]:
    return db.query(Pago).filter(Pago.id == pago_id).first()


def obtener_pagos(db: Session, skip: int = 0, limit: int = 100) -> List[Pago]:
    return db.query(Pago).offset(skip).limit(limit).all()


def obtener_pagos_por_asignacion(db: Session, asignacion_id: int) -> List[Pago]:
    return db.query(Pago).filter(Pago.asignacion_id == asignacion_id).all()


def obtener_pagos_por_estado(db: Session, estado: bool, skip: int = 0, limit: int = 100) -> List[Pago]:
    return db.query(Pago).filter(
        Pago.estado == estado
    ).offset(skip).limit(limit).all()


def actualizar_pago(db: Session, pago_id: int, pago_update: PagoUpdate) -> Optional[Pago]:
    db_pago = obtener_pago(db, pago_id)
    if not db_pago:
        return None
    
    update_data = pago_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_pago, field, value)
    
    db.commit()
    db.refresh(db_pago)
    return db_pago


def obtener_pagos_por_taller(db: Session, taller_id: int) -> List[Pago]:
    """Obtiene todos los pagos asociados a un taller a través de sus asignaciones"""
    return db.query(Pago).join(Asignacion, Pago.asignacion_id == Asignacion.id).filter(
        Asignacion.taller_id == taller_id
    ).all()


def eliminar_pago(db: Session, pago_id: int) -> bool:
    db_pago = obtener_pago(db, pago_id)
    if not db_pago:
        return False
    
    db.delete(db_pago)
    db.commit()
    return True