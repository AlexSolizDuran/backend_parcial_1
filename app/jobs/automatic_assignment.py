import asyncio
import logging
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from app.modulos.asignacion.model import Asignacion, EstadoAsignacion
from app.modulos.asignacion import service as asignacion_service
from app.modulos.incidentes.models.incidente import Incidente
from app.modulos.incidentes.services.incidente import buscar_talleres_cercanos
from app.modulos.incidentes.services.notificacion import NotificacionService
from app.modulos.activos.models.taller import Taller
from app.modulos.usuarios.models.tecnico import Tecnico

logger = logging.getLogger(__name__)

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    # 1. datetime.utcnow() toma la hora del servidor en Render (que es UTC)
    # 2. Le restamos 4 horas fijas (hardcodeado)
    # 3. Devuelve un datetime "limpio" sin zona horaria, así la BD guarda exactamente esos números.
    return datetime.utcnow() - timedelta(hours=4)


def _notify_async(coro):
    """Helper para ejecutar coroutines de forma síncrona"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


def _crear_notificacion_cliente(db: Session, cliente_id: int, titulo: str, mensaje: str, tipo: str):
    """Guarda notificación en BD para el cliente"""
    from app.modulos.usuarios.services.notificacion import crear_notificacion
    from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
    try:
        crear_notificacion(db, NotificacionCreate(
            usuario_id=cliente_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo
        ))
    except Exception as e:
        logger.error(f"Error creando notificación: {e}")


def obtener_talleres_disponibles(db: Session, taller_ids: List[int]) -> List[int]:
    """Retorna IDs de talleres que tienen al menos un técnico disponible"""
    disponibles = []
    for taller_id in taller_ids:
        tecnicos = db.query(Tecnico).filter(
            Tecnico.taller_id == taller_id,
            Tecnico.disponible == True
        ).first()
        if tecnicos:
            disponibles.append(taller_id)
    return disponibles


def obtener_talleres_con_especialidad(db: Session, taller_ids: List[int], especialidad: str) -> List[int]:
    """Retorna IDs de talleres que tienen la especialidad requerida"""
    if not especialidad or not taller_ids:
        return taller_ids
    
    from app.modulos.activos.models.especialidad import Especialidad, taller_especialidades

    especialidad_lower = especialidad.lower()
    especialidad_obj = db.query(Especialidad).filter(
        Especialidad.nombre.ilike(f"%{especialidad_lower}%")
    ).first()
    
    if not especialidad_obj:
        return taller_ids
    
    from sqlalchemy import select
    stmt = select(taller_especialidades.c.taller_id).where(
        taller_especialidades.c.taller_id.in_(taller_ids),
        taller_especialidades.c.especialidad_id == especialidad_obj.id
    )
    resultados = db.execute(stmt).all()
    return [r[0] for r in resultados]


def obtener_siguiente_talleres(db: Session, incidente_id: int, especialidad: str = None, radio_km: float = 10.0) -> List[int]:
    """Busca talleres disponibles para un incidente, excluyendo rechazados y aceptados"""
    incidente = db.query(Incidente).filter(Incidente.id == incidente_id).first()
    if not incidente:
        return []
    
    todas_asignaciones = db.query(Asignacion).filter(
        Asignacion.incidente_id == incidente_id
    ).all()
    
    rechazados_ids = set()
    asignados_ids = set()
    aceptados_ids = set()
    
    for a in todas_asignaciones:
        if a.taller_id:
            rechazados_ids.add(a.taller_id)
        
        if a.estado == EstadoAsignacion.aceptada:
            aceptados_ids.add(a.taller_id)
        elif a.estado == EstadoAsignacion.pendiente:
            asignados_ids.add(a.taller_id)
    
    talleres = buscar_talleres_cercanos(
        db, incidente.ubicacion_lat, incidente.ubicacion_lng, radio_km
    )
    
    talleres_ids = [t.id for t in talleres if t.id not in rechazados_ids and t.id not in aceptados_ids]
    
    if especialidad:
        talleres_ids = obtener_talleres_con_especialidad(db, talleres_ids, especialidad)
    
    talleres_ids = obtener_talleres_disponibles(db, talleres_ids)
    
    return talleres_ids


def verificar_asignaciones_expiradas(db: Session) -> List[dict]:
    """Verifica asignaciones pendientes expiradas y reintenta asignación"""
    resultados = []
    ahora = now_bolivia()
    
    asignaciones_expiradas = db.query(Asignacion).filter(
        Asignacion.estado == EstadoAsignacion.pendiente,
        Asignacion.fecha_expiracion != None,
        Asignacion.fecha_expiracion <= ahora
    ).all()
    
    for asignacion in asignaciones_expiradas:
        reload_asignacion = db.query(Asignacion).filter(Asignacion.id == asignacion.id).first()
        if not reload_asignacion or reload_asignacion.estado != EstadoAsignacion.pendiente:
            continue
        
        incidente = db.query(Incidente).filter(Incidente.id == reload_asignacion.incidente_id).first()
        if not incidente or not incidente.estado:
            continue
        
        # Verificar si ya fue asignado o necesita más información
        if incidente.estado.value in ['asignado', 'finalizado', 'cancelado', 'sin_talleres']:
            continue
        
        # Verificar si requiere más evidencia - no reasignar
        if incidente.requiere_mas_evidencia == 1:
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        # Verificar si ya fue analizado por IA
        if not incidente.especialidad_ia or incidente.especialidad_ia == 'desconocido':
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        # VERIFICAR si ya hay una asignación aceptada - si es así, NO procesar más
        asignacion_aceptada = db.query(Asignacion).filter(
            Asignacion.incidente_id == incidente.id,
            Asignacion.estado == EstadoAsignacion.aceptada
        ).first()
        if asignacion_aceptada:
            # Ya hay una aceptada - marcar esta como expirada y cancelar otras pendientes
            reload_asignacion.estado = EstadoAsignacion.expirada
            reload_asignacion.rechazados_ids = reload_asignacion.rechazados_ids + f",{reload_asignacion.taller_id}" if reload_asignacion.rechazados_ids else str(reload_asignacion.taller_id)
            
            # Cancelar otras asignaciones pendientes por si acaso
            otras_pendientes = db.query(Asignacion).filter(
                Asignacion.incidente_id == incidente.id,
                Asignacion.estado == EstadoAsignacion.pendiente,
                Asignacion.id != reload_asignacion.id
            ).all()
            for otra in otras_pendientes:
                otra.estado = EstadoAsignacion.cancelada
            db.commit()
            continue
        
        reload_asignacion.estado = EstadoAsignacion.expirada
        reload_asignacion.rechazados_ids = reload_asignacion.rechazados_ids + f",{reload_asignacion.taller_id}" if reload_asignacion.rechazados_ids else str(reload_asignacion.taller_id)
        db.commit()
        
        _notify_async(NotificacionService.notificar_cliente_expirado(db, incidente.cliente_id, incidente.id, reload_asignacion.taller_id))
        
        taller_exp = db.query(Taller).filter(Taller.id == reload_asignacion.taller_id).first()
        taller_exp_nombre = taller_exp.nombre if taller_exp else "Taller"
        _crear_notificacion_cliente(
            db, incidente.cliente_id,
            "Tiempo de espera agotado",
            f"El taller {taller_exp_nombre} no respondió a tiempo. Buscando otro taller...",
            "taller_expirado"
        )
        
        # VERIFICAR si ya hay asignación aceptada ANTES de buscar otro taller
        asignacion_aceptada_existente = db.query(Asignacion).filter(
            Asignacion.incidente_id == incidente.id,
            Asignacion.estado == EstadoAsignacion.aceptada
        ).first()
        if asignacion_aceptada_existente:
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        # Verificar si ya hay asignación completada
        asignacion_completada = db.query(Asignacion).filter(
            Asignacion.incidente_id == incidente.id,
            Asignacion.estado == EstadoAsignacion.completada
        ).first()
        if asignacion_completada:
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        # Verificar si el incidente ya está en estado final
        if incidente.estado.value in ['asignado', 'en_camino', 'en_sitio', 'finalizado']:
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        siguientes = obtener_siguiente_talleres(
            db, incidente.id, incidente.especialidad_ia, 10.0
        )
        
        # Verificar que el incidente ya fue analizado por IA antes de asignar
        if not siguientes or not incidente or not incidente.especialidad_ia or incidente.especialidad_ia == 'desconocido' or incidente.requiere_mas_evidencia == 1:
            reload_asignacion.estado = EstadoAsignacion.expirada
            db.commit()
            continue
        
        if siguientes:
            nuevo_taller_id = siguientes[0]
            nueva_asignacion = asignacion_service.crear_asignacion(
                db, incidente.id, nuevo_taller_id, EstadoAsignacion.pendiente, 2
            )
            db.commit()
            
            taller = db.query(Taller).filter(Taller.id == nuevo_taller_id).first()
            
            _notify_async(NotificacionService.notificar_taller_nuevo_incidente(
                db, nuevo_taller_id, incidente.id, incidente.especialidad_ia, incidente.prioridad
            ))
            
            resultados.append({
                "asignacion_id": reload_asignacion.id,
                "nuevo_taller_id": nuevo_taller_id,
                "nueva_asignacion_id": nueva_asignacion.id,
                "taller_nombre": taller.nombre if taller else "Desconocido"
            })
        else:
            incidente.estado = "sin_talleres"
            db.commit()
            
            _notify_async(NotificacionService.notificar_cliente_sin_talleres(db, incidente.cliente_id, incidente.id, incidente.especialidad_ia))
            
            _crear_notificacion_cliente(
                db, incidente.cliente_id,
                "Sin talleres disponibles",
                f"No hay talleres disponibles con la especialidad {incidente.especialidad_ia or 'requerida'} en tu zona.",
                "sin_talleres"
            )
            
            resultados.append({
                "asignacion_id": reload_asignacion.id,
                "sin_talleres": True,
                "incidente_id": incidente.id
            })
    
    return resultados


def reintentar_asignacion(db: Session, incidente_id: int, taller_rechazado_id: int) -> dict:
    """Cuando un taller rechaza, busca el siguiente disponible"""
    incidente = db.query(Incidente).filter(Incidente.id == incidente_id).first()
    if not incidente or not incidente.estado:
        return {"success": False, "error": "Incidente no encontrado o sin estado"}
    
    # Verificar si el incidente ya fue analizado por IA
    # Si no tiene especialidad_ia, significa que aún no fue analizado
    if not incidente.especialidad_ia or incidente.especialidad_ia == 'desconocido':
        return {"success": False, "error": "Incidente aún no ha sido analizado por IA"}
    
    # Si requiere más información, no buscar taller
    if incidente.requiere_mas_evidencia == 1:
        return {"success": False, "error": "Se requiere más información del incidente"}
    
    # Ya fue asignado o finalizado - no reintentar
    if incidente.estado.value in ['asignado', 'en_camino', 'en_sitio', 'finalizado']:
        return {"success": False, "error": "Incidente ya asignado o finalizado"}
    
    # Si está en sin_talleres, verificar si ya hay asignación aceptada
    if incidente.estado.value == 'sin_talleres':
        asignacion_existente = db.query(Asignacion).filter(
            Asignacion.incidente_id == incidente_id,
            Asignacion.estado.in_([EstadoAsignacion.aceptada, EstadoAsignacion.completada])
        ).first()
        if asignacion_existente:
            return {"success": False, "error": "Incidente ya tiene asignación aceptada"}
    
    # Verificar si YA HAY una asignación aceptada para este incidente
    asignacion_ya_aceptada = db.query(Asignacion).filter(
        Asignacion.incidente_id == incidente_id,
        Asignacion.estado == EstadoAsignacion.aceptada
    ).first()
    if asignacion_ya_aceptada:
        return {"success": False, "error": "Este incidente ya tiene una asignación aceptada"}
    
    siguientes = obtener_siguiente_talleres(
        db, incidente.id, incidente.especialidad_ia, 10.0
    )
    
    if not siguientes:
        incidente.estado = "sin_talleres"
        db.commit()
        _notify_async(NotificacionService.notificar_cliente_sin_talleres(db, incidente.cliente_id, incidente.id, incidente.especialidad_ia))
        _crear_notificacion_cliente(
            db, incidente.cliente_id,
            "Sin talleres disponibles",
            f"No hay talleres disponibles con la especialidad {incidente.especialidad_ia or 'requerida'} en tu zona.",
            "sin_talleres"
        )
        return {"success": True, "sin_talleres": True, "incidente_id": incidente.id}
    
    nuevo_taller_id = siguientes[0]
    nueva_asignacion = asignacion_service.crear_asignacion(
        db, incidente.id, nuevo_taller_id, EstadoAsignacion.pendiente, 2
    )
    db.commit()
    
    taller = db.query(Taller).filter(Taller.id == nuevo_taller_id).first()
    taller_rechazado = db.query(Taller).filter(Taller.id == taller_rechazado_id).first()
    taller_rechazado_nombre = taller_rechazado.nombre if taller_rechazado else "Taller"
    
    _notify_async(NotificacionService.notificar_taller_nuevo_incidente(
        db, nuevo_taller_id, incidente.id, incidente.especialidad_ia, incidente.prioridad
    ))
    _notify_async(NotificacionService.notificar_cliente_rechazo(db, incidente.cliente_id, incidente.id, taller_rechazado_id))
    
    _crear_notificacion_cliente(
        db, incidente.cliente_id,
        "Taller no disponible",
        f"El taller {taller_rechazado_nombre} no puede atenderte. Buscando otro taller...",
        "taller_rechazo"
    )
    
    return {
        "success": True,
        "nuevo_taller_id": nuevo_taller_id,
        "nueva_asignacion_id": nueva_asignacion.id,
        "taller_nombre": taller.nombre if taller else "Desconocido"
    }