from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError
from typing import Optional

from app.db.database import get_db
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.usuarios.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse, Login
from app.modulos.usuarios.services import usuario as usuario_service
from app.core.config import settings

router = APIRouter(prefix="/usuario")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/usuario/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = usuario_service.obtener_usuario_por_username(db, username)
    if user is None:
        raise credentials_exception
    return user


def get_current_user_with_taller(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        taller_id: Optional[int] = payload.get("taller_id")
        nombre_taller: Optional[str] = payload.get("nombre_taller")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = usuario_service.obtener_usuario_por_username(db, username)
    if user is None:
        raise credentials_exception
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "nombre": user.nombre,
        "telefono": user.telefono,
        "rol": user.rol,
        "created_at": user.created_at,
        "taller_id": taller_id,
        "nombre_taller": nombre_taller
    }


@router.post("/register", response_model=UsuarioResponse)
def register(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = usuario_service.crear_usuario(db, usuario)
    if not db_usuario:
        raise HTTPException(status_code=400, detail="Email o username ya registrado")
    return db_usuario


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = usuario_service.autenticar_usuario(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario_service.crear_token(user, db)


@router.get("/me", response_model=UsuarioResponse)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user


@router.get("/me/taller")
def get_me_with_taller(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from jose import jwt
    from app.modulos.usuarios.models.usuario import RolEnum
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    username: str = payload.get("sub")
    taller_id: Optional[int] = payload.get("taller_id")
    nombre_taller: Optional[str] = payload.get("nombre_taller")
    
    user = usuario_service.obtener_usuario_por_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "nombre": user.nombre,
        "telefono": user.telefono,
        "rol": user.rol.value,
        "taller_id": taller_id,
        "nombre_taller": nombre_taller
    }


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    db_usuario = usuario_service.obtener_usuario(db, usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_usuario


@router.get("/", response_model=list[UsuarioResponse])
def get_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return usuario_service.obtener_usuarios(db, skip, limit)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(usuario_id: int, usuario: UsuarioUpdate, db: Session = Depends(get_db)):
    db_usuario = usuario_service.actualizar_usuario(db, usuario_id, usuario)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_usuario


@router.delete("/{usuario_id}")
def delete_usuario(usuario_id: int, db: Session = Depends(get_db)):
    print(usuario_id)
    db_usuario = usuario_service.eliminar_usuario(db, usuario_id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Usuario eliminado"}
