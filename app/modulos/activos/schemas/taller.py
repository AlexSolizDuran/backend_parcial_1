from pydantic import BaseModel
from typing import Optional, List


class EspecialidadBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class EspecialidadCreate(EspecialidadBase):
    pass


class EspecialidadResponse(EspecialidadBase):
    id: int

    class Config:
        from_attributes = True


class TallerBase(BaseModel):
    nombre: str
    ubicacion_lat: float
    ubicacion_lng: float
    telefono: Optional[str] = None
    horario_atencion: Optional[str] = None


class TallerCreate(TallerBase):
    especialidades: List[int] = []


class TallerUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None
    telefono: Optional[str] = None
    horario_atencion: Optional[str] = None


class TallerResponse(TallerBase):
    id: int
    dueño_id: int
    especialidades: List[EspecialidadResponse] = []

    class Config:
        from_attributes = True


class TallerSimpleResponse(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class HistorialTallerBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    tipo: str


class HistorialTallerCreate(HistorialTallerBase):
    pass


class HistorialTallerResponse(HistorialTallerBase):
    id: int
    taller_id: int
    fecha: str

    class Config:
        from_attributes = True