from pydantic import BaseModel, Field
from typing import Optional, List
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
    estado: EstadoIncidente
    requiere_mas_evidencia: Optional[int] = 0
    mensaje_solicitud: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class EvidenciaBase(BaseModel):
    tipo: str  # foto, audio, texto
    url_archivo: Optional[str] = None
    contenido: Optional[str] = None


class EvidenciaCreate(EvidenciaBase):
    incidente_id: int


class EvidenciaResponse(EvidenciaBase):
    id: int
    incidente_id: int
    contenido: Optional[str] = None
    transcripcion: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_subida: datetime

    class Config:
        from_attributes = True


class HistoriaIncidenteBase(BaseModel):
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


class AsignacionBase(BaseModel):
    incidente_id: int
    taller_id: int
    tecnico_id: Optional[int] = None


class AsignacionCreate(AsignacionBase):
    pass


class AsignacionUpdate(BaseModel):
    estado: Optional[str] = None
    fecha_aceptacion: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None


class AsignacionResponse(AsignacionBase):
    id: int
    estado: str
    fecha_asignacion: datetime
    fecha_aceptacion: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalisisCompletoRequest(BaseModel):
    """Request para analizar todas las evidencias de un incidente"""
    pass


class AnalisisCompletoResponse(BaseModel):
    """Respuesta con el análisis completo de todas las evidencias"""
    especialidad_ia: str
    descripcion_ia: str
    prioridad: PrioridadIncidente
    descripcion: str