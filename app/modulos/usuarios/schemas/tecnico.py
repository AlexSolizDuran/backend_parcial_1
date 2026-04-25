from pydantic import BaseModel
from typing import Optional


class TecnicoBase(BaseModel):
    taller_id: Optional[int] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None


class TecnicoCreate(TecnicoBase):
    pass


class TecnicoUpdate(BaseModel):
    disponible: Optional[bool] = None


class UsuarioTecnicoResponse(BaseModel):
    id: int
    nombre: str
    email: str
    username: str
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class TecnicoResponse(TecnicoBase):
    id: int
    usuario_id: int
    disponible: bool
    usuario: Optional[UsuarioTecnicoResponse] = None

    class Config:
        from_attributes = True
