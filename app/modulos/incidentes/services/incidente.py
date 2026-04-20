from sqlalchemy.orm import Session
from typing import List, Optional
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente, PrioridadIncidente
from app.modulos.incidentes.models.evidencia import Evidencia
from app.modulos.incidentes.models.historial import HistoriaIncidente
from app.modulos.incidentes.models.asignacion import Asignacion, EstadoAsignacion
from app.modulos.incidentes.schemas.incidente import IncidenteCreate, IncidenteUpdate, EvidenciaCreate, HistoriaIncidenteCreate
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.activos.models.taller import Taller
from app.modulos.activos.models.vehiculo import Vehiculo
from datetime import datetime
import math


MAP_ESTADO_INCIDENTE_A_HISTORIA = {
    EstadoIncidente.reportado: "recibido",
    EstadoIncidente.asignado: "asignado",
    EstadoIncidente.en_camino: "en_atencion",
    EstadoIncidente.en_sitio: "en_atencion",
    EstadoIncidente.finalizado: "completado",
    EstadoIncidente.cancelado: "cancelado",
}


def crear_incidente(db: Session, incidente: IncidenteCreate) -> Incidente:
    """Create a new incident report"""
    db_incidente = Incidente(
        cliente_id=incidente.cliente_id,
        vehiculo_id=incidente.vehiculo_id,
        ubicacion_lat=incidente.ubicacion_lat,
        ubicacion_lng=incidente.ubicacion_lng,
        descripcion_original=incidente.descripcion_original
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


def obtener_incidente(db: Session, incidente_id: int) -> Optional[Incidente]:
    """Get incident by ID"""
    return db.query(Incidente).filter(Incidente.id == incidente_id).first()


def obtener_incidentes_cliente(db: Session, cliente_id: int, skip: int = 0, limit: int = 100) -> List[Incidente]:
    """Get all incidents for a specific client"""
    return db.query(Incidente).filter(
        Incidente.cliente_id == cliente_id
    ).offset(skip).limit(limit).all()


def obtener_incidentes_taller(db: Session, taller_id: int, skip: int = 0, limit: int = 100) -> List[Incidente]:
    """Get all incidents assigned to a specific taller"""
    return db.query(Incidente).join(Asignacion).filter(
        Asignacion.taller_id == taller_id
    ).offset(skip).limit(limit).all()


def actualizar_incidente(db: Session, incidente_id: int, incidente_update: IncidenteUpdate) -> Optional[Incidente]:
    """Update incident with AI analysis results"""
    db_incidente = obtener_incidente(db, incidente_id)
    if not db_incidente:
        return None
    
    update_data = incidente_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_incidente, field, value)
    
    db_incidente.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(db_incidente)
    return db_incidente


def agregar_evidencia(db: Session, evidencia: EvidenciaCreate, transcripcion: Optional[str] = None, descripcion: Optional[str] = None) -> Evidencia:
    """Add evidence (photo/audio/texto) to an incident"""
    db_evidencia = Evidencia(
        incidente_id=evidencia.incidente_id,
        tipo=evidencia.tipo,
        url_archivo=evidencia.url_archivo,
        contenido=evidencia.contenido,
        transcripcion=transcripcion,
        descripcion=descripcion
    )
    db.add(db_evidencia)
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def obtener_evidencias_incidente(db: Session, incidente_id: int) -> List[Evidencia]:
    """Get all evidences for an incident"""
    return db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()


def cambiar_estado_incidente(db: Session, incidente_id: int, nuevo_estado: EstadoIncidente, notas: Optional[str] = None) -> Optional[Incidente]:
    """Change incident state and record in history"""
    db_incidente = obtener_incidente(db, incidente_id)
    if not db_incidente:
        return None
    
    estado_anterior = db_incidente.estado
    db_incidente.estado = nuevo_estado
    db_incidente.fecha_actualizacion = datetime.utcnow()
    
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


def crear_asignacion(db: Session, incidente_id: int, taller_id: int) -> Asignacion:
    """Assign incident to a taller"""
    db_asignacion = Asignacion(
        incidente_id=incidente_id,
        taller_id=taller_id,
        estado=EstadoAsignacion.pendiente
    )
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def obtener_asignaciones_incidente(db: Session, incidente_id: int) -> List[Asignacion]:
    """Get all assignments for an incident"""
    return db.query(Asignacion).filter(Asignacion.incidente_id == incidente_id).all()


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


def actualizar_asignacion(db: Session, asignacion_id: int, estado: EstadoAsignacion, 
                         tecnico_id: Optional[int] = None) -> Optional[Asignacion]:
    """Update assignment status"""
    db_asignacion = db.query(Asignacion).filter(Asignacion.id == asignacion_id).first()
    if not db_asignacion:
        return None
    
    db_asignacion.estado = estado
    if estado == EstadoAsignacion.aceptada:
        db_asignacion.fecha_aceptacion = datetime.utcnow()
    elif tecnico_id:
        db_asignacion.tecnico_id = tecnico_id
    
    db.commit()
    db.refresh(db_asignacion)
    return db_asignacion


def calcular_distancia(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula (in kilometers)"""
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def buscar_talleres_cercanos(db: Session, lat: float, lng: float, radio_km: float = 10.0, 
                           especialidad: Optional[str] = None) -> List[Taller]:
    """Find workshops within a given radius"""
    all_talleres = db.query(Taller).filter(Taller.activo == True).all()
    
    talleres_cercanos = []
    for taller in all_talleres:
        distancia = calcular_distancia(lat, lng, taller.ubicacion_lat, taller.ubicacion_lng)
        if distancia <= radio_km:
            if especialidad is None:
                talleres_cercanos.append((taller, distancia))
            else:
                for esp in taller.especialidades:
                    if esp.nombre == especialidad:
                        talleres_cercanos.append((taller, distancia))
                        break
    
    talleres_cercanos.sort(key=lambda x: x[1])
    return [taller for taller, _ in talleres_cercanos]


def obtener_estadisticas_incidente(db: Session, incidente_id: int) -> dict:
    """Get statistics and AI analysis for an incident"""
    incidente = obtener_incidente(db, incidente_id)
    if not incidente:
        return {}
    
    evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()
    historia = db.query(HistoriaIncidente).filter(HistoriaIncidente.incidente_id == incidente_id).order_by(HistoriaIncidente.fecha_hora.desc()).all()
    asignaciones = db.query(Asignacion).filter(Asignacion.incidente_id == incidente_id).all()
    
    return {
        "incidente": incidente,
        "evidencias": evidencias,
        "historial": historia,
        "asignaciones": asignaciones,
        "total_evidencias": len(evidencias),
        "tiene_foto": any(e.tipo == "foto" for e in evidencias),
        "tiene_audio": any(e.tipo == "audio" for e in evidencias),
        "tiene_texto": any(e.tipo == "texto" for e in evidencias)
    }