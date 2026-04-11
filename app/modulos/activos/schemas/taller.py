from pydantic import BaseModel
from typing import Optional


class TallerBase(BaseModel):
    nombre: str
    ubicacion_lat: float
    ubicacion_lng: float
    especialidad: str
    telefono: Optional[str] = None
    horario_atencion: Optional[str] = None


class TallerCreate(TallerBase):
    pass


class TallerUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None
    especialidad: Optional[str] = None
    telefono: Optional[str] = None
    horario_atencion: Optional[str] = None


class TallerResponse(TallerBase):
    id: int
    dueño_id: int

    class Config:
        from_attributes = True
