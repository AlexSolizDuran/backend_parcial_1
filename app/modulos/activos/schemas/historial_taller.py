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
    fecha: str

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            taller_id=obj.taller_id,
            titulo=obj.titulo,
            descripcion=obj.descripcion,
            tipo=obj.tipo,
            fecha=obj.fecha.isoformat() if obj.fecha else None
        )

    class Config:
        from_attributes = True