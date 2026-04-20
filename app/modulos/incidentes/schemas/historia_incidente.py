from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HistoriaIncidenteBase(BaseModel):
    estado: str
    titulo: str
    descripcion: Optional[str] = None


class HistoriaIncidenteCreate(HistoriaIncidenteBase):
    pass


class HistoriaIncidenteResponse(HistoriaIncidenteBase):
    id: int
    incidente_id: int
    fecha_hora: datetime

    class Config:
        from_attributes = True