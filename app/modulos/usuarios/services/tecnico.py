from sqlalchemy.orm import Session

from app.modulos.usuarios.models.tecnico import Tecnico
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.usuarios.schemas.tecnico import TecnicoCreate, TecnicoUpdate


def crear_tecnico(db: Session, usuario_id: int):
    db_tecnico = db.query(Tecnico).filter(Tecnico.usuario_id == usuario_id).first()
    if db_tecnico:
        return None

    db_tecnico = Tecnico(
        usuario_id=usuario_id,
        disponible=True
    )
    db.add(db_tecnico)
    db.commit()
    db.refresh(db_tecnico)
    return db_tecnico


def crear_tecnico_por_usuario_id(db: Session, usuario_id: int, taller_id: int, disponible: bool = True):
    db_tecnico = db.query(Tecnico).filter(Tecnico.usuario_id == usuario_id).first()
    if db_tecnico:
        db_tecnico.taller_id = taller_id
        db_tecnico.disponible = disponible
        db.commit()
        db.refresh(db_tecnico)
        return db_tecnico
    
    db_tecnico = Tecnico(
        usuario_id=usuario_id,
        taller_id=taller_id,
        disponible=disponible
    )
    db.add(db_tecnico)
    db.commit()
    db.refresh(db_tecnico)
    return db_tecnico


def obtener_tecnico(db: Session, tecnico_id: int):
    return db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()


def obtener_tecnico_por_usuario(db: Session, usuario_id: int):
    return db.query(Tecnico).filter(Tecnico.usuario_id == usuario_id).first()


def obtener_tecnicos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Tecnico).offset(skip).limit(limit).all()


def obtener_tecnicos_por_taller(db: Session, taller_id: int, skip: int = 0, limit: int = 100):
    return db.query(Tecnico).filter(Tecnico.taller_id == taller_id).offset(skip).limit(limit).all()


def obtener_tecnicos_disponibles(db: Session, taller_id: int = None):
    query = db.query(Tecnico).filter(Tecnico.disponible == True)
    if taller_id:
        query = query.filter(Tecnico.taller_id == taller_id)
    return query.all()


def actualizar_disponibilidad(db: Session, tecnico_id: int, disponible: bool):
    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        return None

    db_tecnico.disponible = disponible
    db.commit()
    db.refresh(db_tecnico)
    return db_tecnico


def asignar_taller(db: Session, tecnico_id: int, taller_id: int, disponible: bool):
    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        return None

    db_tecnico.taller_id = taller_id
    db_tecnico.disponible = disponible
    db.commit()
    db.refresh(db_tecnico)
    return db_tecnico


def eliminar_tecnico(db: Session, tecnico_id: int):
    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        return None

    db.delete(db_tecnico)
    db.commit()
    return db_tecnico
