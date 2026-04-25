from pydantic import BaseModel
from typing import Optional


class PagoBase(BaseModel):
    monto_total: float
    monto_comision: float
    asignacion_id: Optional[int] = None


class PagoCreate(PagoBase):
    pass


class PagoUpdate(BaseModel):
    monto_total: Optional[float] = None
    monto_comision: Optional[float] = None
    estado: Optional[bool] = None


class PagoResponse(PagoBase):
    id: int
    estado: bool

    class Config:
        from_attributes = True