from sqlalchemy.orm import Session

from app.modulos.usuarios.models.notificacion import Notificacion
from app.modulos.usuarios.schemas.notificacion import NotificacionCreate, NotificacionUpdate


def crear_notificacion(db: Session, notificacion: NotificacionCreate):
    db_notificacion = Notificacion(
        usuario_id=notificacion.usuario_id,
        titulo=notificacion.titulo,
        mensaje=notificacion.mensaje,
        tipo=notificacion.tipo
    )
    
    db.add(db_notificacion)
    db.commit()
    db.refresh(db_notificacion)
    return db_notificacion


def obtener_notificacion(db: Session, notificacion_id: int):
    return db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()


def obtener_notificaciones_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    return db.query(Notificacion).filter(
        Notificacion.usuario_id == usuario_id
    ).offset(skip).limit(limit).all()


def marcar_como_leido(db: Session, notificacion_id: int):
    db_notificacion = db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
    if not db_notificacion:
        return None

    db_notificacion.leido = True
    db.commit()
    db.refresh(db_notificacion)
    return db_notificacion


def eliminar_notificacion(db: Session, notificacion_id: int):
    db_notificacion = db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
    if not db_notificacion:
        return None

    db.delete(db_notificacion)
    db.commit()
    return db_notificacion
