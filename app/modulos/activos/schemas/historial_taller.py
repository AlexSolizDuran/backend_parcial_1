from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HistorialTallerBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    tipo: str


class HistorialTallerCreate(HistorialTallerBase):
    pass


class HistorialTallerResponse(HistorialTallerBase):
    id: int
    taller_id: int
    fecha: datetime

    class Config:
        from_attributes = True