from app.core.websocket.manager import ws_manager
from app.modulos.incidentes.services.incidente import buscar_talleres_cercanos
from app.modulos.activos.models.historial_taller import HistorialTaller
from app.modulos.asignacion import service as asignacion_service
from app.modulos.asignacion.model import EstadoAsignacion
from app.modulos.usuarios.models.tecnico import Tecnico
from app.modulos.activos.models.taller import Taller
from app.modulos.incidentes.models.incidente import Incidente
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def _crear_historial_taller(db: Session, taller_id: int, titulo: str, descripcion: str, tipo: str):
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo=titulo,
        descripcion=descripcion,
        tipo=tipo
    )
    db.add(db_historial)
    db.commit()


def _taller_tiene_tecnicos_disponibles(db: Session, taller_id: int) -> bool:
    return db.query(Tecnico).filter(
        Tecnico.taller_id == taller_id,
        Tecnico.disponible == True
    ).first() is not None


def _taller_tiene_especialidad(db: Session, taller_id: int, especialidad: str) -> bool:
    if not especialidad:
        return True
    from app.modulos.activos.models.especialidad import Especialidad, taller_especialidades
    
    especialidad_lower = especialidad.lower()
    especialidad_obj = db.query(Especialidad).filter(
        Especialidad.nombre.ilike(f"%{especialidad_lower}%")
    ).first()
    
    if not especialidad_obj:
        return True
    
    from sqlalchemy import select
    stmt = select(taller_especialidades).where(
        taller_especialidades.c.taller_id == taller_id,
        taller_especialidades.c.especialidad_id == especialidad_obj.id
    )
    result = db.execute(stmt).first()
    return result is not None


class NotificacionService:
    @staticmethod
    async def notificar_incidente_cercano(
        db: Session,
        incidente_id: int,
        lat: float,
        lng: float,
        radio_km: float = 10.0,
        especialidad: str = None,
        prioridad: str = None,
        timeout_minutos: int = 2
    ):
        try:
            talleres_cercanos = buscar_talleres_cercanos(db, lat, lng, radio_km)
            
            if not talleres_cercanos:
                logger.info(f"No talleres found within {radio_km}km of incident {incidente_id}")
                return []
            
            talleres_validos = []
            for taller in talleres_cercanos:
                if not _taller_tiene_tecnicos_disponibles(db, taller.id):
                    continue
                if not _taller_tiene_especialidad(db, taller.id, especialidad):
                    continue
                talleres_validos.append(taller)
            
            if not talleres_validos:
                logger.info(f"No talleres with available tecnicos and specialty {especialidad} found")
                return []
            
            asignaciones_creadas = []
            
            for taller in talleres_validos:
                _crear_historial_taller(
                    db, taller.id,
                    titulo="Nuevo incidente requiere atención",
                    descripcion=f"Nuevo incidente reportado. Especialidad: {especialidad or 'General'}",
                    tipo="incidente_llegada"
                )
                
                asignacion = asignacion_service.crear_asignacion(
                    db, incidente_id, taller.id,
                    EstadoAsignacion.pendiente, timeout_minutos
                )
                asignaciones_creadas.append({
                    "taller_id": taller.id,
                    "taller_nombre": taller.nombre,
                    "asignacion_id": asignacion.id
                })
                
                await NotificacionService.notificar_taller_nuevo_incidente(
                    db, taller.id, incidente_id, especialidad, prioridad
                )
            
            logger.info(f"Created {len(asignaciones_creadas)} assignments for incident {incidente_id}")
            return asignaciones_creadas
            
        except Exception as e:
            logger.error(f"Error notifying nearby talleres: {e}")
            return []

    @staticmethod
    async def notificar_taller_nuevo_incidente(
        db: Session,
        taller_id: int,
        incidente_id: int,
        especialidad: str,
        prioridad: str
    ):
        incidente = db.query(Incidente).filter(Incidente.id == incidente_id).first()
        if not incidente:
            return
        
        taller = db.query(Taller).filter(Taller.id == taller_id).first()
        asignacion = db.query(asignacion_service.Asignacion).filter(
            asignacion_service.Asignacion.incidente_id == incidente_id,
            asignacion_service.Asignacion.taller_id == taller_id
        ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()
        
        message = {
            "type": "nuevo_incidente",
            "incidente_id": incidente_id,
            "especialidad": especialidad,
            "prioridad": prioridad,
            "descripcion_ia": incidente.descripcion_ia,
            "lat": incidente.ubicacion_lat,
            "lng": incidente.ubicacion_lng,
            "asignacion_id": asignacion.id if asignacion else None,
            "timeout_minutos": 2
        }
        await ws_manager.send_to_taller(message, taller_id)
        
        if taller and taller.dueño_id:
            from app.modulos.usuarios.services.notificacion import crear_notificacion
            from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
            
            crear_notificacion(db, NotificacionCreate(
                usuario_id=taller.dueño_id,
                titulo="Nuevo incidente asignado",
                mensaje=f"Incidente #{incidente_id} - {especialidad or 'General'}",
                tipo="nuevo_incidente"
            ))

    @staticmethod
    async def notificar_cliente_rechazo(
        db: Session,
        cliente_id: int,
        incidente_id: int,
        taller_rechazado_id: int
    ):
        taller = db.query(Taller).filter(Taller.id == taller_rechazado_id).first()
        taller_nombre = taller.nombre if taller else "Taller"
        
        message = {
            "type": "taller_rechazo",
            "incidente_id": incidente_id,
            "mensaje": f"El taller {taller_nombre} no puede atenderte. Buscando otro taller...",
            "taller_nombre": taller_nombre
        }
        await ws_manager.send_to_cliente(message, cliente_id)

    @staticmethod
    async def notificar_cliente_expirado(
        db: Session,
        cliente_id: int,
        incidente_id: int,
        taller_id: int
    ):
        taller = db.query(Taller).filter(Taller.id == taller_id).first()
        taller_nombre = taller.nombre if taller else "Taller"
        
        message = {
            "type": "taller_expirado",
            "incidente_id": incidente_id,
            "mensaje": f"El taller {taller_nombre} no respondió a tiempo. Buscando otro taller...",
            "taller_nombre": taller_nombre
        }
        await ws_manager.send_to_cliente(message, cliente_id)

    @staticmethod
    async def notificar_cliente_sin_talleres(
        db: Session,
        cliente_id: int,
        incidente_id: int,
        especialidad: str
    ):
        message = {
            "type": "sin_talleres",
            "incidente_id": incidente_id,
            "mensaje": f"No hay talleres disponibles con la especialidad {especialidad or 'requerida'} en tu zona. Te contactaremos pronto.",
            "especialidad": especialidad
        }
        await ws_manager.send_to_cliente(message, cliente_id)

    @staticmethod
    async def notificar_cliente_asignado(
        db: Session,
        cliente_id: int,
        incidente_id: int,
        taller_id: int
    ):
        taller = db.query(Taller).filter(Taller.id == taller_id).first()
        taller_nombre = taller.nombre if taller else "Taller"
        
        message = {
            "type": "incidente_asignado",
            "incidente_id": incidente_id,
            "mensaje": f"Tu incidente ha sido asignado al taller {taller_nombre}",
            "taller_id": taller_id,
            "taller_nombre": taller_nombre
        }
        await ws_manager.send_to_cliente(message, cliente_id)

    @staticmethod
    async def notificar_incidente_creado(
        db: Session,
        cliente_id: int,
        incidente_id: int
    ):
        message = {
            "type": "incidente_creado",
            "incidente_id": incidente_id,
            "mensaje": "Tu incidente ha sido reportado. Te informaremos cuando sea analizado."
        }
        await ws_manager.send_to_cliente(message, cliente_id)

    @staticmethod
    async def notificar_cambio_estado(
        incidente_id: int,
        cliente_id: int,
        nuevo_estado: str,
        mensaje: str = None
    ):
        message = {
            "type": "cambio_estado",
            "incidente_id": incidente_id,
            "estado": nuevo_estado,
            "mensaje": mensaje or f"El incidente ha cambiado a estado: {nuevo_estado}"
        }
        await ws_manager.send_to_cliente(message, cliente_id)
    
    @staticmethod
    async def notificar_asignacion(
        incidente_id: int,
        taller_id: int,
        mensaje: str = "Se te ha asignado un nuevo incidente"
    ):
        message = {
            "type": "asignacion_incidente",
            "incidente_id": incidente_id,
            "mensaje": mensaje
        }
        await ws_manager.send_to_taller(message, taller_id)
    
    @staticmethod
    async def notificar_analisis_completo(
        db: Session,
        cliente_id: int,
        incidente_id: int,
        especialidad_ia: str,
        prioridad: str,
        descripcion: str
    ):
        message = {
            "type": "analisis_ia_completo",
            "incidente_id": incidente_id,
            "especialidad_ia": especialidad_ia,
            "prioridad": prioridad,
            "descripcion": descripcion,
            "mensaje": f"Tu incidente ha sido analizado. Especialidad: {especialidad_ia or 'General'}"
        }
        await ws_manager.send_to_cliente(message, cliente_id)