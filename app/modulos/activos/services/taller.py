from sqlalchemy.orm import Session

from app.modulos.activos.models.taller import Taller
from app.modulos.activos.schemas.taller import TallerCreate, TallerUpdate


def crear_taller(db: Session, dueño_id: int, taller: TallerCreate):
    db_taller = db.query(Taller).filter(Taller.dueño_id == dueño_id).first()
    if db_taller:
        return None

    db_taller = Taller(
        dueño_id=dueño_id,
        nombre=taller.nombre,
        ubicacion_lat=taller.ubicacion_lat,
        ubicacion_lng=taller.ubicacion_lng,
        especialidad=taller.especialidad,
        telefono=taller.telefono,
        horario_atencion=taller.horario_atencion
    )
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


def obtener_talleres_por_especialidad(db: Session, especialidad: str):
    return db.query(Taller).filter(Taller.especialidad == especialidad).all()


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


def eliminar_taller(db: Session, taller_id: int):
    db_taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not db_taller:
        return None

    db.delete(db_taller)
    db.commit()
    return db_taller
