from pydantic import BaseModel
from typing import Optional


class VehiculoBase(BaseModel):
    placa: str
    modelo: str
    marca: str
    color: Optional[str] = None


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(BaseModel):
    placa: Optional[str] = None
    modelo: Optional[str] = None
    marca: Optional[str] = None
    color: Optional[str] = None


class VehiculoResponse(VehiculoBase):
    id: int
    cliente_id: int

    class Config:
        from_attributes = True
