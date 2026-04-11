from sqlalchemy.orm import Session
from datetime import timedelta

from app.modulos.usuarios.models.usuario import Usuario, RolEnum
from app.modulos.usuarios.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.modulos.activos.models.taller import Taller


def crear_usuario(db: Session, usuario: UsuarioCreate):
    db_usuario = db.query(Usuario).filter(
        (Usuario.email == usuario.email) | (Usuario.username == usuario.username)
    ).first()
    if db_usuario:
        return None

    hashed_password = get_password_hash(usuario.password)
    db_usuario = Usuario(
        email=usuario.email,
        username=usuario.username,
        hashed_password=hashed_password,
        nombre=usuario.nombre,
        telefono=usuario.telefono,
        rol=usuario.rol.value
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def obtener_usuario(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def obtener_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Usuario).offset(skip).limit(limit).all()


def obtener_usuario_por_username(db: Session, username: str):
    return db.query(Usuario).filter(Usuario.username == username).first()


def actualizar_usuario(db: Session, usuario_id: int, usuario: UsuarioUpdate):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not db_usuario:
        return None

    if usuario.email:
        db_usuario.email = usuario.email
    if usuario.username:
        db_usuario.username = usuario.username
    if usuario.nombre:
        db_usuario.nombre = usuario.nombre
    if usuario.telefono:
        db_usuario.telefono = usuario.telefono

    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def eliminar_usuario(db: Session, usuario_id: int):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    print(db_usuario)
    if not db_usuario:
        return None

    db.delete(db_usuario)
    db.commit()
    return db_usuario


def autenticar_usuario(db: Session, username: str, password: str):
    user = obtener_usuario_por_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def crear_token(usuario: Usuario, db: Session = None):
    token_data = {
        "sub": usuario.username,
        "rol": usuario.rol
    }
    
    if usuario.rol == RolEnum.dueno and db:
        taller = db.query(Taller).filter(Taller.dueño_id == usuario.id).first()
        token_data["taller_id"] = taller.id if taller else None
        token_data["nombre_taller"] = taller.nombre if taller else None
    
    access_token = create_access_token(data=token_data)
    return {"access_token": access_token, "token_type": "bearer"}
