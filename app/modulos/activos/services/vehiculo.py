from sqlalchemy.orm import Session

from app.modulos.activos.models.vehiculo import Vehiculo
from app.modulos.activos.schemas.vehiculo import VehiculoCreate, VehiculoUpdate


def crear_vehiculo(db: Session, cliente_id: int, vehiculo: VehiculoCreate):
    db_vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == vehiculo.placa).first()
    if db_vehiculo:
        return None

    db_vehiculo = Vehiculo(
        cliente_id=cliente_id,
        placa=vehiculo.placa,
        modelo=vehiculo.modelo,
        marca=vehiculo.marca,
        color=vehiculo.color
    )
    db.add(db_vehiculo)
    db.commit()
    db.refresh(db_vehiculo)
    return db_vehiculo


def obtener_vehiculo(db: Session, vehiculo_id: int):
    return db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()


def obtener_vehiculos_cliente(db: Session, cliente_id: int):
    return db.query(Vehiculo).filter(Vehiculo.cliente_id == cliente_id).all()


def obtener_vehiculos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Vehiculo).offset(skip).limit(limit).all()


def actualizar_vehiculo(db: Session, vehiculo_id: int, vehiculo: VehiculoUpdate):
    db_vehiculo = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not db_vehiculo:
        return None

    update_data = vehiculo.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vehiculo, key, value)

    db.commit()
    db.refresh(db_vehiculo)
    return db_vehiculo


def eliminar_vehiculo(db: Session, vehiculo_id: int):
    db_vehiculo = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not db_vehiculo:
        return None

    db.delete(db_vehiculo)
    db.commit()
    return db_vehiculo
