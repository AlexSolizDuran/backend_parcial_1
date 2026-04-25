from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.modulos.activos.models.vehiculo import Vehiculo
from app.modulos.activos.schemas.vehiculo import VehiculoCreate, VehiculoUpdate, VehiculoResponse
from app.modulos.activos.services import vehiculo as vehiculo_service
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.usuarios.models.usuario import Usuario

router = APIRouter(prefix="/vehiculo", tags=["vehiculos"])


@router.post("", response_model=VehiculoResponse)
def crear_vehiculo(
    vehiculo: VehiculoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "cliente":
        raise HTTPException(status_code=403, detail="Solo clientes pueden registrar vehiculos")
    
    db_vehiculo = vehiculo_service.crear_vehiculo(db, current_user.id, vehiculo)
    if not db_vehiculo:
        raise HTTPException(status_code=400, detail="Vehiculo con esta placa ya existe")
    return db_vehiculo


@router.get("/mis-vehiculos-del-cliente", response_model=List[VehiculoResponse])
def get_mis_vehiculos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return vehiculo_service.obtener_vehiculos_cliente(db, current_user.id)


@router.get("/{vehiculo_id}", response_model=VehiculoResponse)
def get_vehiculo(vehiculo_id: int, db: Session = Depends(get_db)):
    db_vehiculo = vehiculo_service.obtener_vehiculo(db, vehiculo_id)
    if not db_vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    return db_vehiculo


@router.get("", response_model=List[VehiculoResponse])
def get_vehiculos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return vehiculo_service.obtener_vehiculos(db, skip, limit)


@router.put("/{vehiculo_id}", response_model=VehiculoResponse)
def update_vehiculo(
    vehiculo_id: int,
    vehiculo: VehiculoUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_vehiculo = vehiculo_service.obtener_vehiculo(db, vehiculo_id)
    if not db_vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    if db_vehiculo.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este vehiculo")
    
    return vehiculo_service.actualizar_vehiculo(db, vehiculo_id, vehiculo)


@router.delete("/{vehiculo_id}")
def delete_vehiculo(
    vehiculo_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_vehiculo = vehiculo_service.obtener_vehiculo(db, vehiculo_id)
    if not db_vehiculo:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    if db_vehiculo.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este vehiculo")
    
    vehiculo_service.eliminar_vehiculo(db, vehiculo_id)
    return {"message": "Vehiculo eliminado"}