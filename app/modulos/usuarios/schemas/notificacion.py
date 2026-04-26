from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificacionBase(BaseModel):
    titulo: str
    mensaje: str
    tipo: str = "alerta"


class NotificacionCreate(NotificacionBase):
    usuario_id: int


class NotificacionUpdate(BaseModel):
    leido: Optional[bool] = None


class NotificacionResponse(NotificacionBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    usuario_id: int
    fecha_envio: datetime
    leido: bool