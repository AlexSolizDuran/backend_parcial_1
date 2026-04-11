from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class RolEnum(str, Enum):
    cliente = "cliente"
    dueno = "dueno"
    tecnico = "tecnico"


class UsuarioBase(BaseModel):
    email: EmailStr
    username: str
    nombre: str
    telefono: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str
    rol: RolEnum = RolEnum.cliente


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    nombre: Optional[str] = None
    telefono: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    id: int
    rol: RolEnum
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Login(BaseModel):
    username: str
    password: str
