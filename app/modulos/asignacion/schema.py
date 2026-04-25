from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AsignacionBase(BaseModel):
    incidente_id: int
    taller_id: int
    tecnico_id: Optional[int] = None


class AsignacionCreate(AsignacionBase):
    pass


class AsignacionUpdate(BaseModel):
    estado: Optional[str] = None
    fecha_aceptacion: Optional[datetime] = None
    tecnico_id: Optional[int] = None


class AsignacionResponse(AsignacionBase):
    id: int
    estado: str
    fecha_asignacion: datetime
    fecha_expiracion: Optional[datetime] = None
    fecha_aceptacion: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenciaResponse(BaseModel):
    id: int
    tipo: str
    url_archivo: Optional[str] = None
    contenido: Optional[str] = None
    descripcion: Optional[str] = None
    transcripcion: Optional[str] = None

    class Config:
        from_attributes = True


class ClienteResponse(BaseModel):
    id: int
    nombre: str
    telefono: Optional[str] = None

    class Config:
        from_attributes = True


class VehiculoResponse(BaseModel):
    id: int
    placa: str
    marca: Optional[str] = None
    modelo: Optional[str] = None

    class Config:
        from_attributes = True


class IncidenteDetalleResponse(BaseModel):
    id: int
    ubicacion_lat: float
    ubicacion_lng: float
    especialidad_ia: Optional[str] = None
    descripcion_ia: Optional[str] = None
    prioridad: Optional[str] = None
    descripcion: Optional[str] = None
    cliente: ClienteResponse
    vehiculo: Optional[VehiculoResponse] = None
    evidencias: List[EvidenciaResponse] = []

    class Config:
        from_attributes = True


class AsignacionPendienteDetalleResponse(BaseModel):
    asignacion: AsignacionResponse
    incidente: IncidenteDetalleResponse
    tiempo_restante_segundos: int