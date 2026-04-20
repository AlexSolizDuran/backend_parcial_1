from app.core.websocket.manager import ws_manager
from app.modulos.incidentes.services.incidente import buscar_talleres_cercanos
from app.modulos.activos.models.historial_taller import HistorialTaller
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def _crear_historial_taller(db: Session, taller_id: int, titulo: str, descripcion: str, tipo: str):
    """Helper to create historial entry for a taller"""
    db_historial = HistorialTaller(
        taller_id=taller_id,
        titulo=titulo,
        descripcion=descripcion,
        tipo=tipo
    )
    db.add(db_historial)
    db.commit()


class NotificacionService:
    """Service for sending notifications to talleres"""
    
    @staticmethod
    async def notificar_incidente_cercano(
        db: Session,
        incidente_id: int,
        lat: float,
        lng: float,
        radio_km: float = 10.0
    ):
        """Find nearby talleres and notify them about a new incident"""
        try:
            # Find nearby talleres
            talleres_cercanos = buscar_talleres_cercanos(db, lat, lng, radio_km)
            
            if not talleres_cercanos:
                logger.info(f"No talleres found within {radio_km}km of incident {incidente_id}")
                return
            
            # Get taller IDs
            taller_ids = [t.id for t in talleres_cercanos]
            
            # Create historial entries for each taller
            for taller in talleres_cercanos:
                _crear_historial_taller(
                    db, taller.id,
                    titulo="Nuevo incidente cercano",
                    descripcion=f"Se detectó un nuevo incidente a {radio_km}km de distancia",
                    tipo="incidente_llegada"
                )
            
            # Prepare notification message
            message = {
                "type": "nuevo_incidente",
                "incidente_id": incidente_id,
                "message": f"Nuevo incidente reportado a {radio_km}km de distancia",
                "lat": lat,
                "lng": lng,
                "talleres_notificados": taller_ids
            }
            
            # Send notification to all nearby talleres
            await ws_manager.notify_nearby_talleres(message, taller_ids)
            
            logger.info(f"Notified {len(taller_ids)} talleres about incident {incidente_id}")
            
        except Exception as e:
            logger.error(f"Error notifying nearby talleres: {e}")
    
    @staticmethod
    async def notificar_cambio_estado(
        incidente_id: int,
        cliente_id: int,
        nuevo_estado: str,
        mensaje: str = None
    ):
        """Notify about status change of an incident"""
        message = {
            "type": "cambio_estado",
            "incidente_id": incidente_id,
            "estado": nuevo_estado,
            "mensaje": mensaje or f"El incidente ha cambiado a estado: {nuevo_estado}"
        }
        
        # In a real implementation, we would also track which websocket
        # connections belong to which client and send to the specific client
        await ws_manager.broadcast_to_all(message)
    
    @staticmethod
    async def notificar_asignacion(
        incidente_id: int,
        taller_id: int,
        mensaje: str = "Se te ha asignado un nuevo incidente"
    ):
        """Notify a specific taller about a new assignment"""
        message = {
            "type": "asignacion_incidente",
            "incidente_id": incidente_id,
            "mensaje": mensaje
        }
        
        await ws_manager.send_to_taller(message, taller_id)
    
    @staticmethod
    async def notificar_analisis_completo(
        incidente_id: int,
        especialidad_ia: str,
        prioridad: str,
        descripcion: str
    ):
        """Notify that AI analysis is complete for an incident"""
        message = {
            "type": "analisis_ia_completo",
            "incidente_id": incidente_id,
            "especialidad_ia": especialidad_ia,
            "prioridad": prioridad,
            "descripcion": descripcion
        }
        
        await ws_manager.broadcast_to_all(message)