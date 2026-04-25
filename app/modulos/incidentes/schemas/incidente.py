from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.modulos.incidentes.models.incidente import EstadoIncidente, PrioridadIncidente


class IncidenteBase(BaseModel):
    cliente_id: int
    vehiculo_id: Optional[int] = None
    ubicacion_lat: float
    ubicacion_lng: float
    descripcion_original: Optional[str] = None


class IncidenteCreate(IncidenteBase):
    pass


class IncidenteUpdate(BaseModel):
    especialidad_ia: Optional[str] = None
    descripcion_ia: Optional[str] = None
    descripcion: Optional[str] = None
    prioridad: Optional[PrioridadIncidente] = None
    estado: Optional[EstadoIncidente] = None
    requiere_mas_evidencia: Optional[int] = 0
    mensaje_solicitud: Optional[str] = None


class IncidenteResponse(IncidenteBase):
    id: int
    especialidad_ia: Optional[str] = None
    descripcion_ia: Optional[str] = None
    descripcion: Optional[str] = None
    prioridad: Optional[PrioridadIncidente] = None
    estado: Optional[EstadoIncidente] = None
    requiere_mas_evidencia: Optional[int] = 0
    mensaje_solicitud: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class AnalisisCompletoRequest(BaseModel):
    pass


class AnalisisCompletoResponse(BaseModel):
    especialidad_ia: str
    descripcion_ia: str
    prioridad: PrioridadIncidente
    descripcion: str