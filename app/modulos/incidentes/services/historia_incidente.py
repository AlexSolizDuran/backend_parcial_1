from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.modulos.incidentes.models.historial import HistoriaIncidente
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente
from app.modulos.incidentes.schemas.historia_incidente import HistoriaIncidenteCreate

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)


MAP_ESTADO_INCIDENTE_A_HISTORIA = {
    EstadoIncidente.reportado: "recibido",
    EstadoIncidente.asignado: "asignado",
    EstadoIncidente.en_camino: "en_atencion",
    EstadoIncidente.en_sitio: "en_atencion",
    EstadoIncidente.finalizado: "completado",
    EstadoIncidente.cancelado: "cancelado",
    EstadoIncidente.incluido: "inconcluso",
    EstadoIncidente.sin_talleres: "sin_taller",
}


def crear_incidente(db: Session, incidente) -> Incidente:
    """Create a new incident report"""
    db_incidente = Incidente(
        cliente_id=incidente.cliente_id,
        vehiculo_id=incidente.vehiculo_id,
        ubicacion_lat=incidente.ubicacion_lat,
        ubicacion_lng=incidente.ubicacion_lng,
        descripcion_original=incidente.descripcion_original,
        estado=EstadoIncidente.reportado
    )
    db.add(db_incidente)
    db.commit()
    db.refresh(db_incidente)
    
    db_historia = HistoriaIncidente(
        incidente_id=db_incidente.id,
        titulo="Emergencia recibida",
        descripcion=f"Incidente reportado en coordinates ({db_incidente.ubicacion_lat}, {db_incidente.ubicacion_lng})"
    )
    db.add(db_historia)
    db.commit()
    
    return db_incidente


def crear_historia_incidente(db: Session, incidente_id: int, historia: HistoriaIncidenteCreate) -> HistoriaIncidente:
    """Create a new history entry for an incident"""
    db_historia = HistoriaIncidente(
        incidente_id=incidente_id,
        titulo=historia.titulo,
        descripcion=historia.descripcion
    )
    db.add(db_historia)
    db.commit()
    db.refresh(db_historia)
    return db_historia


def obtener_historia_incidente(db: Session, incidente_id: int) -> List[HistoriaIncidente]:
    """Get all history entries for an incident"""
    return db.query(HistoriaIncidente).filter(
        HistoriaIncidente.incidente_id == incidente_id
    ).order_by(HistoriaIncidente.fecha_hora.desc()).all()


def cambiar_estado_incidente(db: Session, incidente_id: int, nuevo_estado: EstadoIncidente, notas: Optional[str] = None) -> Optional[Incidente]:
    """Change incident state and record in history"""
    db_incidente = db.query(Incidente).filter(Incidente.id == incidente_id).first()
    if not db_incidente:
        return None
    
    estado_anterior = db_incidente.estado
    db_incidente.estado = nuevo_estado
    db_incidente.fecha_actualizacion = now_bolivia()
    
    estado_historia = MAP_ESTADO_INCIDENTE_A_HISTORIA.get(nuevo_estado, "en_atencion")
    titulo = f"Estado cambiado a {nuevo_estado.value}"
    descripcion = notas or f"Cambio de {estado_anterior.value} a {nuevo_estado.value}"
    
    db_historia = HistoriaIncidente(
        incidente_id=incidente_id,
        titulo=titulo,
        descripcion=descripcion
    )
    db.add(db_historia)
    db.commit()
    db.refresh(db_incidente)
    return db_incidente