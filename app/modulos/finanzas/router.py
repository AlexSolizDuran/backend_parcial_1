from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.modulos.finanzas import service as pago_service
from app.modulos.finanzas.schema import PagoCreate, PagoUpdate, PagoResponse
from app.modulos.finanzas.pasarela import pasarela_pago
from app.modulos.usuarios.models.usuario import Usuario
from app.core.security import get_current_user
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente

router = APIRouter(prefix="/pagos", tags=["pagos"])


class PagoTarjetaRequest(BaseModel):
    numero_tarjeta: str
    cvv: str
    expira: str
    monto: float
    email: str
    nombre_titular: str
    asignacion_id: Optional[int] = None


class CrearPagoTecnicoRequest(BaseModel):
    monto: float
    incidente_id: int
    finalizar: bool = True


@router.post("/tecnico/crear", status_code=status.HTTP_201_CREATED)
def crear_pago_desde_tecnico(
    request: CrearPagoTecnicoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """El técnico crea el pago al finalizar el incidente"""
    
    db_incidente = db.query(Incidente).filter(Incidente.id == request.incidente_id).first()
    if not db_incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    if request.finalizar:
        db_incidente.estado = EstadoIncidente.finalizado
        db.commit()
        db.refresh(db_incidente)
        
        from app.modulos.asignacion import service as asignacion_service
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        asignacion = db.query(asignacion_service.Asignacion).filter(
            asignacion_service.Asignacion.incidente_id == request.incidente_id
        ).first()
        if asignacion:
            asignacion.estado = asignacion_service.EstadoAsignacion.completada
            db.commit()
        
        db.add(crear_notificacion(
            db, NotificacionCreate(
                usuario_id=db_incidente.cliente_id,
                titulo="Incidente resuelto",
                mensaje=f"Tu incidente ha sido resuelto. Monto Bs {request.monto}. ¡Gracias por usar AUXIA!",
                tipo="incidente_finalizado"
            )
        ))
        db.commit()
    
    monto_comision = round(request.monto * 0.10, 2)
    
    pago_create = PagoCreate(
        monto_total=request.monto,
        monto_comision=monto_comision,
        asignacion_id=None
    )
    
    db_pago = pago_service.crear_pago(db, pago_create)
    db.commit()
    db.refresh(db_pago)
    
    return {
        "exitoso": True,
        "pago": {
            "id": db_pago.id,
            "monto_total": db_pago.monto_total,
            "monto_comision": db_pago.monto_comision,
            "estado": db_pago.estado
        },
        "incidente_estado": db_incidente.estado.value if db_incidente.estado else None
    }


class ReembolsoRequest(BaseModel):
    id_transaccion: str


@router.post("/procesar", status_code=status.HTTP_201_CREATED)
def procesar_pago(
    request: PagoTarjetaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Procesa un pago con tarjeta de crédito/débito"""
    resultado = pasarela_pago.procesar_pago(
        numero_tarjeta=request.numero_tarjeta,
        cvv=request.cvv,
        expira=request.expira,
        monto=request.monto,
        email=request.email,
        nombre_titular=request.nombre_titular
    )
    
    if resultado["exitoso"]:
        if request.asignacion_id:
            monto_comision = round(request.monto * 0.10, 2)
            pago_create = PagoCreate(
                monto_total=request.monto,
                monto_comision=monto_comision,
                asignacion_id=request.asignacion_id
            )
            db_pago = pago_service.crear_pago(db, pago_create)
        
        return {
            "exitoso": True,
            "pago": resultado,
            "registro_db": db_pago.id if request.asignacion_id else None
        }
    
    return {
        "exitoso": False,
        "error": resultado["error"],
        "codigo": resultado.get("codigo", "ERROR")
    }


@router.post("/reembolsar")
def reembolsar_pago(
    request: ReembolsoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Procesa un reembolso"""
    resultado = pasarela_pago.reembolsar_pago(request.id_transaccion)
    return resultado


@router.get("/transaccion/{id_transaccion}")
def obtener_estado_transaccion(
    id_transaccion: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Consulta el estado de una transacción"""
    return pasarela_pago.obtener_estado_transaccion(id_transaccion)


@router.post("/validar-tarjeta")
def validar_tarjeta(
    numero_tarjeta: str,
    cvv: str,
    expira: str
):
    """Valida una tarjeta antes de procesar el pago"""
    validacion_tarjeta = pasarela_pago.validar_tarjeta(numero_tarjeta)
    
    if not validacion_tarjeta["valida"]:
        return {"valida": False, "error": validacion_tarjeta["error"]}
    
    validacion_cvv = pasarela_pago.validar_cvv(cvv, validacion_tarjeta["tipo"])
    if not validacion_cvv:
        return {"valida": False, "error": "CVV inválido"}
    
    validacion_expira = pasarela_pago.validar_expiracion(expira)
    if not validacion_expira["valida"]:
        return {"valida": False, "error": validacion_expira["error"]}
    
    return {
        "valida": True,
        "tipo": validacion_tarjeta["tipo"],
        "ultimos_4": validacion_tarjeta["ultimos_4"]
    }


@router.post("/", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
def crear_pago(
    pago: PagoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return pago_service.crear_pago(db, pago)


@router.get("/", response_model=List[PagoResponse])
def obtener_pagos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return pago_service.obtener_pagos(db, skip=skip, limit=limit)


@router.get("/asignacion/{asignacion_id}", response_model=List[PagoResponse])
def obtener_pagos_por_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return pago_service.obtener_pagos_por_asignacion(db, asignacion_id)


@router.get("/estado/{estado}", response_model=List[PagoResponse])
def obtener_pagos_por_estado(
    estado: bool,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return pago_service.obtener_pagos_por_estado(db, estado, skip=skip, limit=limit)


@router.get("/{pago_id}", response_model=PagoResponse)
def obtener_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    pago = pago_service.obtener_pago(db, pago_id)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )
    return pago


@router.put("/{pago_id}", response_model=PagoResponse)
def actualizar_pago(
    pago_id: int,
    pago_update: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    pago = pago_service.actualizar_pago(db, pago_id, pago_update)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )
    return pago


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    success = pago_service.eliminar_pago(db, pago_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )
    return None