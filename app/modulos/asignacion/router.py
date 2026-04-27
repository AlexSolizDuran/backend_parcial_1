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
async def rechazar_asignacion(
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
    
    # Agregar historial del rechazo
    if incidente:
        from app.modulos.incidentes.models.historial import HistoriaIncidente
        db_historial = HistoriaIncidente(
            incidente_id=incidente.id,
            titulo="Taller rechazado",
            descripcion=f"Taller {taller.nombre} ha rechazado el incidente"
        )
        db.add(db_historial)
    
    asignacion.estado = EstadoAsignacion.rechazada
    asignacion.rechazados_ids = asignacion.rechazados_ids + f",{asignacion.taller_id}" if asignacion.rechazados_ids else str(asignacion.taller_id)
    # Establecer timeout de 10 segundos antes de permitir nuevos intentos para este incidente
    asignacion.proximo_reintento = now_bolivia() + timedelta(seconds=10)
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
        
        # Enviar notificación push al cliente por WebSocket
        from app.modulos.incidentes.services.notificacion import NotificacionService
        await NotificacionService.notificar_cliente_rechazo(
            db=db,
            cliente_id=incidente.cliente_id,
            incidente_id=incidente.id,
            taller_rechazado_id=taller.id
        )
    
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
     
    asignacion_aceptada = asignacion_service.aceptar_asignacion(db, asignacion_id, tecnico_id)
    
    if asignacion_aceptada is None:
        raise HTTPException(
            status_code=409, 
            detail="Este incidente ya tiene una asignación aceptada. No se puede aceptar otra."
        )
    
    # Notificar al cliente y al técnico que la asignación ha sido aceptada
    if incidente:
        from app.modulos.incidentes.services.notificacion import NotificacionService
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        # Notificar al cliente
        await NotificacionService.notificar_cliente_asignado(
            db=db,
            cliente_id=incidente.cliente_id,
            incidente_id=incidente.id,
            taller_id=taller.id
        )
        
        # Notificar al técnico (si se proporcionó)
        if tecnico_id:
            await NotificacionService.notificar_tecnico_por_user_id(
                db=db,
                tecnico_user_id=tecnico_id,
                incidente_id=incidente.id,
                mensaje=f"Se te ha asignado el incidente #{incidente.id}"
            )
        
        # Crear notificación interna en la base de datos para el cliente
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Taller aceptado",
            mensaje=f"El taller {taller.nombre} ha aceptado tu incidente. Te atenderán pronto.",
            tipo="incidente_asignado"
        ))
        db.commit()
    
    # La función ya canceló las demás asignaciones pendientes, no es necesario hacerlo de nuevo
    
    if incidente:
        incidente.estado = EstadoIncidente.asignado
        # Establecer timeout de 10 segundos para evitar búsquedas inmediatas después de aceptación
        # Buscar asignaciones pendientes para este incidente y establecer timeout
        asignaciones_pendientes = db.query(asignacion_service.Asignacion).filter(
            asignacion_service.Asignacion.incidente_id == incidente.id,
            asignacion_service.Asignacion.estado == EstadoAsignacion.pendiente
        ).all()
        for asignacion in asignaciones_pendientes:
            asignacion.proximo_reintento = now_bolivia() + timedelta(seconds=10)
        db.commit()
        
        from app.modulos.incidentes.services import historia_incidente as historia_service
        db_historial = historia_service.HistoriaIncidente(
            incidente_id=incidente.id,
            titulo="Técnico asignado",
            descripcion=f"Taller {taller.nombre} ha aceptado el incidente y asignado un técnico"
        )
        db.add(db_historial)
        db.commit()
        
        await NotificacionService.notificar_cliente_asignado(
            db=db,
            cliente_id=incidente.cliente_id,
            incidente_id=incidente.id,
            taller_id=taller.id
        )
        
        await NotificacionService.notificar_tecnico_por_user_id(
            db=db,
            tecnico_user_id=tecnico.usuario_id,
            incidente_id=incidente.id,
            mensaje=f"Se te ha asignado el incidente #{incidente.id}"
        )
        
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Taller aceptado",
            mensaje=f"El taller {taller.nombre} ha aceptado tu incidente. Te atenderán pronto.",
            tipo="incidente_asignado"
        ))
        db.commit()
    
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
    """Acepta un incidente y asigna un técnico actualizando la asignación pendiente"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.incidentes.models.incidente import EstadoIncidente
    from app.modulos.usuarios.services.notificacion import crear_notificacion
    from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
    from app.modulos.incidentes.services import historia_incidente as historia_service
    from app.modulos.asignacion.model import EstadoAsignacion

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

    # 1. BUSCAR LA ASIGNACIÓN PENDIENTE ORIGINAL
    asignacion_pendiente = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.incidente_id == data.incidente_id,
        asignacion_service.Asignacion.taller_id == taller.id,
        asignacion_service.Asignacion.estado == EstadoAsignacion.pendiente
    ).first()

    if not asignacion_pendiente:
        raise HTTPException(status_code=400, detail="No hay una asignación pendiente para aceptar o ya fue aceptada.")

    # 2. ACTUALIZAR LA ASIGNACIÓN (NO CREAR UNA NUEVA)
    asignacion_pendiente.estado = EstadoAsignacion.aceptada
    asignacion_pendiente.tecnico_id = data.tecnico_id
    from app.modulos.asignacion.model import now_bolivia
    asignacion_pendiente.fecha_aceptacion = now_bolivia()
    
    # 3. CANCELAR OTRAS ASIGNACIONES PENDIENTES (Si el sistema le avisó a múltiples talleres)
    otras_pendientes = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.incidente_id == data.incidente_id,
        asignacion_service.Asignacion.estado == EstadoAsignacion.pendiente,
        asignacion_service.Asignacion.id != asignacion_pendiente.id
    ).all()
    for otra in otras_pendientes:
        otra.estado = EstadoAsignacion.cancelada

    incidente.estado = EstadoIncidente.asignado
    db.commit()

    # --- El resto del código de notificaciones se mantiene igual ---
    from app.modulos.incidentes.schemas.historia_incidente import HistoriaIncidenteCreate
    historia = HistoriaIncidenteCreate(
        titulo="Incidente asignado",
        descripcion=f"Asignado a técnico {tecnico.usuario.nombre if tecnico.usuario else ''}"
    )
    historia_service.crear_historia_incidente(db, data.incidente_id, historia)

    # Notificar al cliente
    db.add(crear_notificacion(
        db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Incidente aceptado",
            mensaje=f"El taller {taller.nombre} ha aceptado tu incidente. Te atenderán pronto.",
            tipo="incidente_aceptado"
        )
    ))
    
    # Notificar al técnico
    from app.modulos.usuarios.models.usuario import Usuario as UsuarioModel
    cliente = db.query(UsuarioModel).filter(UsuarioModel.id == incidente.cliente_id).first()
    
    db.add(crear_notificacion(
        db, NotificacionCreate(
            usuario_id=tecnico.usuario_id,
            titulo="Nuevo incidente asignado",
            mensaje=f"Se te ha asignado el incidente #{incidente.id}. Cliente: {cliente.nombre if cliente else ''}",
            tipo="incidente_asignado_tecnico"
        )
    ))
    
    # Enviar notificación push al técnico
    try:
        from app.modulos.incidentes.services.firebase_service import send_push_notification
        tecnico_usuario = db.query(UsuarioModel).filter(UsuarioModel.id == tecnico.usuario_id).first()
        if tecnico_usuario and tecnico_usuario.fcm_token:
            send_push_notification(
                token_fcm=tecnico_usuario.fcm_token,
                titulo="Nuevo incidente asignado",
                mensaje=f"Se te ha asignado el incidente #{incidente.id}. Cliente: {cliente.nombre if cliente else ''}",
                data={
                    "incidente_id": str(incidente.id),
                    "tipo": "incidente_asignado"
                }
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error al enviar push al técnico: {e}")
    
    # Enviar notificación push al cliente
    try:
        cliente_usuario = db.query(UsuarioModel).filter(UsuarioModel.id == incidente.cliente_id).first()
        if cliente_usuario and cliente_usuario.fcm_token:
            send_push_notification(
                token_fcm=cliente_usuario.fcm_token,
                titulo="Técnico asignado",
                mensaje=f"El taller {taller.nombre} ha asignado un técnico a tu incidente #{incidente.id}",
                data={
                    "incidente_id": str(incidente.id),
                    "tipo": "incidente_asignado"
                }
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error al enviar push al cliente: {e}")
    
    db.commit()

    return {
        "asignacion_id": asignacion_pendiente.id,
        "estado": "aceptada",
        "incidente_id": asignacion_pendiente.incidente_id,
        "taller_id": asignacion_pendiente.taller_id
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