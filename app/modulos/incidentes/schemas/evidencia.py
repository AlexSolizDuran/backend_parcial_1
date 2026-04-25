from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EvidenciaBase(BaseModel):
    tipo: str
    url_archivo: Optional[str] = None
    contenido: Optional[str] = None


class EvidenciaCreate(EvidenciaBase):
    incidente_id: int


class EvidenciaUpdate(BaseModel):
    tipo: Optional[str] = None
    url_archivo: Optional[str] = None
    contenido: Optional[str] = None
    transcripcion: Optional[str] = None
    descripcion: Optional[str] = None


class EvidenciaResponse(EvidenciaBase):
    id: int
    incidente_id: int
    transcripcion: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_subida: datetime

    class Config:
        from_attributes = True