from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from typing import Optional
from datetime import timedelta
import asyncio

from app.db.database import get_db
from app.modulos.asignacion import service as asignacion_service
from app.modulos.asignacion.schema import (
    AsignacionCreate, AsignacionUpdate, AsignacionResponse,
    AsignacionPendienteDetalleResponse, IncidenteDetalleResponse,
    EvidenciaResponse, ClienteResponse, VehiculoResponse, AceptarYAsignarSchema
)
from app.modulos.asignacion.model import EstadoAsignacion, now_bolivia
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.activos.models.taller import Taller
from app.core.security import get_current_user
from app.jobs.automatic_assignment import reintentar_asignacion, verificar_asignaciones_expiradas
from app.modulos.incidentes.services.notificacion import NotificacionService

router = APIRouter(prefix="/asignaciones", tags=["asignaciones"])


@router.post("/", response_model=AsignacionResponse, status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    asignacion: AsignacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return asignacion_service.crear_asignacion(db, asignacion)


@router.get("/", response_model=List[AsignacionResponse])
def obtener_asignaciones(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return asignacion_service.obtener_asignaciones(db, skip=skip, limit=limit)


@router.get("/taller/{taller_id}", response_model=List[AsignacionResponse])
def obtener_asignaciones_por_taller(
    taller_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return asignacion_service.obtener_asignaciones_por_taller(db, taller_id, skip=skip, limit=limit)


@router.get("/taller/{taller_id}/pendiente", response_model=AsignacionPendienteDetalleResponse | None)
def obtener_asignacion_pendiente(
    taller_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este taller")
    
    asignacion = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.taller_id == taller_id,
        asignacion_service.Asignacion.estado == EstadoAsignacion.pendiente,
        asignacion_service.Asignacion.fecha_expiracion != None,
        asignacion_service.Asignacion.fecha_expiracion > now_bolivia()
    ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()
    
    if not asignacion:
        return None
    
    incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
    if not incidente:
        return None
    
    from app.modulos.usuarios.models.usuario import Usuario as UsuarioModel
    from app.modulos.activos.models.vehiculo import Vehiculo
    from app.modulos.incidentes.models.evidencia import Evidencia
    
    cliente = db.query(UsuarioModel).filter(UsuarioModel.id == incidente.cliente_id).first()
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()
    evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente.id).all()
    
    # Manejar timezone-aware y naive
    now = now_bolivia()
    fecha_exp = asignacion.fecha_expiracion
    if fecha_exp is None:
        tiempo_restante = 0
    elif fecha_exp.tzinfo is None:
        # fecha naive - convertir a aware
        from datetime import timezone
        fecha_exp_aware = fecha_exp.replace(tzinfo=timezone(timedelta(hours=-4)))
        tiempo_restante = max(0, int((fecha_exp_aware - now).total_seconds()))
    else:
        tiempo_restante = max(0, int((fecha_exp - now).total_seconds()))
    
    return AsignacionPendienteDetalleResponse(
        asignacion=AsignacionResponse(
            id=asignacion.id,
            incidente_id=asignacion.incidente_id,
            taller_id=asignacion.taller_id,
            tecnico_id=asignacion.tecnico_id,
            estado=asignacion.estado.value,
            fecha_asignacion=asignacion.fecha_asignacion,
            fecha_expiracion=asignacion.fecha_expiracion,
            fecha_aceptacion=asignacion.fecha_aceptacion,
            fecha_inicio=asignacion.fecha_inicio,
            fecha_fin=asignacion.fecha_fin
        ),
        incidente=IncidenteDetalleResponse(
            id=incidente.id,
            ubicacion_lat=incidente.ubicacion_lat,
            ubicacion_lng=incidente.ubicacion_lng,
            especialidad_ia=incidente.especialidad_ia,
            descripcion_ia=incidente.descripcion_ia,
            prioridad=incidente.prioridad.value if incidente.prioridad else None,
            descripcion=incidente.descripcion,
            cliente=ClienteResponse(
                id=cliente.id,
                nombre=cliente.nombre,
                telefono=cliente.telefono
            ),
            vehiculo=VehiculoResponse(
                id=vehiculo.id,
                placa=vehiculo.placa,
                marca=vehiculo.marca,
                modelo=vehiculo.modelo
            ) if vehiculo else None,
            evidencias=[
                EvidenciaResponse(
                    id=e.id,
                    tipo=e.tipo,
                    url_archivo=e.url_archivo,
                    contenido=e.contenido,
                    descripcion=e.descripcion,
                    transcripcion=e.transcripcion
                ) for e in evidencias
            ]
        ),
        tiempo_restante_segundos=tiempo_restante
    )


@router.get("/incidente/{incidente_id}", response_model=List[AsignacionResponse])
def obtener_asignaciones_por_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return asignacion_service.obtener_asignaciones_por_incidente(db, incidente_id)


@router.get("/{asignacion_id}", response_model=AsignacionResponse)
def obtener_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    asignacion = asignacion_service.obtener_asignacion(db, asignacion_id)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada"
        )
    return asignacion


@router.put("/{asignacion_id}", response_model=AsignacionResponse)
def actualizar_asignacion(
    asignacion_id: int,
    asignacion_update: AsignacionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    asignacion = asignacion_service.actualizar_asignacion(db, asignacion_id, asignacion_update)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada"
        )
    return asignacion


@router.put("/{asignacion_id}/rechazar", response_model=dict)
def rechazar_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    asignacion = asignacion_service.obtener_asignacion(db, asignacion_id)
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    
    taller = db.query(Taller).filter(Taller.id == asignacion.taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para rechazar esta asignación")
    
    if asignacion.estado != EstadoAsignacion.pendiente:
        raise HTTPException(status_code=400, detail="Solo puedes rechazar asignaciones pendientes")
    
    incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
    
    asignacion.estado = EstadoAsignacion.rechazada
    db.commit()
    
    if incidente and incidente.cliente_id:
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Taller no disponible",
            mensaje=f"El taller {taller.nombre} no puede atenderte. Buscando otro taller...",
            tipo="taller_rechazo"
        ))
    
    resultado = reintentar_asignacion(db, asignacion.incidente_id, asignacion.taller_id)
    
    return {
        "asignacion_id": asignacion_id,
        "estado": "rechazada",
        "resultado": resultado
    }


@router.put("/{asignacion_id}/aceptar", response_model=dict)
async def aceptar_asignacion_incidente(
    asignacion_id: int,
    tecnico_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    asignacion = asignacion_service.obtener_asignacion(db, asignacion_id)
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    
    taller = db.query(Taller).filter(Taller.id == asignacion.taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para aceptar esta asignación")
    
    if asignacion.estado != EstadoAsignacion.pendiente:
        raise HTTPException(status_code=400, detail="Solo puedes aceptar asignaciones pendientes")
    
    incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
    
    asignacion_service.aceptar_asignacion(db, asignacion_id, tecnico_id)
    
    if incidente:
        incidente.estado = EstadoIncidente.asignado
        db.commit()
        
        asyncio.create_task(
            NotificacionService.notificar_cliente_asignado(
                db=db,
                cliente_id=incidente.cliente_id,
                incidente_id=incidente.id,
                taller_id=taller.id
            )
        )
        
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Taller aceptado",
            mensaje=f"El taller {taller.nombre} ha aceptado tu incidente. Te atenderán pronto.",
            tipo="incidente_asignado"
        ))
    
    return {
        "asignacion_id": asignacion_id,
        "estado": "aceptada",
        "incidente_id": asignacion.incidente_id,
        "taller_id": asignacion.taller_id
    }


@router.post("/aceptar-y-asignar")
def aceptar_y_asignar_tecnico(
    data: AceptarYAsignarSchema,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Acepta un incidente y asigna un técnico -> crea asignación aceptada"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.incidentes.models.incidente import EstadoIncidente
    from app.modulos.usuarios.services.notificacion import crear_notificacion
    from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
    from app.modulos.incidentes.services import historia_incidente as historia_service

    if current_user.rol.value != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden aceptar incidentes")

    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="No tienes taller registrado")

    tecnico = db.query(Tecnico).filter(Tecnico.id == data.tecnico_id).first()
    if not tecnico or tecnico.taller_id != taller.id:
        raise HTTPException(status_code=404, detail="Técnico no encontrado en tu taller")

    from app.modulos.incidentes.models.incidente import Incidente
    incidente = db.query(Incidente).filter(Incidente.id == data.incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    if incidente.estado not in [EstadoIncidente.reportado, EstadoIncidente.sin_talleres]:
        raise HTTPException(status_code=400, detail="El incidente ya fue asignado")

    existente = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.incidente_id == data.incidente_id,
        asignacion_service.Asignacion.taller_id == taller.id,
        asignacion_service.Asignacion.estado == EstadoAsignacion.aceptada
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya tienes una asignación aceptada para este incidente")

    asignacion = asignacion_service.crear_asignacion_aceptada(
        db, data.incidente_id, taller.id, data.tecnico_id
    )

    incidente.estado = EstadoIncidente.asignado
    db.commit()

    historia_service.crear_historia_incidente(db, data.incidente_id, "Incidente asignado", 
                                          f"Asignado a técnico {tecnico.usuario.nombre if tecnico.usuario else ''}")

    # Notificar al cliente
    db.add(crear_notificacion(
        db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Incidente aceptado",
            mensaje=f"El taller {taller.nombre} ha aceptado tu incidente. Te atenderán pronto.",
            tipo="incidente_aceptado"
        )
    ))
    db.commit()

    return {
        "asignacion_id": asignacion.id,
        "estado": "aceptada",
        "incidente_id": asignacion.incidente_id,
        "taller_id": asignacion.taller_id
    }


@router.post("/verificar-expiradas", response_model=List[dict])
def verificar_expiradas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.rol.value != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden verificar asignaciones expiradas")
    
    resultados = verificar_asignaciones_expiradas(db)
    return resultados


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    success = asignacion_service.eliminar_asignacion(db, asignacion_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada"
        )
    return None