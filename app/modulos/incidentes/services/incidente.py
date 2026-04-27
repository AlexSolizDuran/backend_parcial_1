from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente, PrioridadIncidente
from app.modulos.incidentes.models.evidencia import Evidencia
from app.modulos.incidentes.models.historial import HistoriaIncidente
from app.modulos.asignacion.model import Asignacion
from app.modulos.asignacion import service as asignacion_service
from app.modulos.incidentes.schemas.incidente import IncidenteCreate, IncidenteUpdate
from app.modulos.incidentes.services.historia_incidente import (
    crear_historia_incidente,
    obtener_historia_incidente as obtener_historia,
    cambiar_estado_incidente as cambiar_estado_historia
)
from app.modulos.activos.models.taller import Taller

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)
import math


def crear_incidente(db: Session, incidente: IncidenteCreate) -> Incidente:
    from app.modulos.incidentes.services.historia_incidente import crear_incidente as crear_incidente_historia
    return crear_incidente_historia(db, incidente)


def obtener_incidente(db: Session, incidente_id: int) -> Optional[Incidente]:
    return db.query(Incidente).filter(Incidente.id == incidente_id).first()


def obtener_incidentes_cliente(db: Session, cliente_id: int, skip: int = 0, limit: int = 100) -> List[Incidente]:
    return db.query(Incidente).filter(
        Incidente.cliente_id == cliente_id
    ).offset(skip).limit(limit).all()


def obtener_incidentes_taller(db: Session, taller_id: int, skip: int = 0, limit: int = 100) -> List[Incidente]:
    return db.query(Incidente).join(Asignacion).filter(
        Asignacion.taller_id == taller_id
    ).offset(skip).limit(limit).all()


def actualizar_incidente(db: Session, incidente_id: int, incidente_update: IncidenteUpdate) -> Optional[Incidente]:
    db_incidente = obtener_incidente(db, incidente_id)
    if not db_incidente:
        return None
    
    update_data = incidente_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_incidente, field, value)
    
    db_incidente.fecha_actualizacion = now_bolivia()
    db.commit()
    db.refresh(db_incidente)
    return db_incidente


def cambiar_estado_incidente(db: Session, incidente_id: int, nuevo_estado: EstadoIncidente, notas: Optional[str] = None) -> Optional[Incidente]:
    return cambiar_estado_historia(db, incidente_id, nuevo_estado, notas)


def obtener_historia_incidente(db: Session, incidente_id: int) -> List[HistoriaIncidente]:
    return obtener_historia(db, incidente_id)


def calcular_distancia(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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
    all_talleres = db.query(Taller).all()
    
    talleres_cercanos = []
    for taller in all_talleres:
        distancia = calcular_distancia(lat, lng, taller.ubicacion_lat, taller.ubicacion_lng)
        if distancia <= radio_km:
            if especialidad is None:
                talleres_cercanos.append((taller, distancia))
            else:
                for esp in taller.especialidades:
                    if esp.nombre.lower() == especialidad.lower():
                        talleres_cercanos.append((taller, distancia))
                        break
    
    talleres_cercanos.sort(key=lambda x: x[1])
    return [taller for taller, _ in talleres_cercanos]


def obtener_estadisticas_incidente(db: Session, incidente_id: int) -> dict:
    incidente = obtener_incidente(db, incidente_id)
    if not incidente:
        return {}
    
    from app.modulos.incidentes.services import evidencia as evidencia_service
    
    evidencias = evidencia_service.obtener_evidencias_incidente(db, incidente_id)
    historia = obtener_historia_incidente(db, incidente_id)
    asignaciones = asignacion_service.obtener_asignaciones_por_incidente(db, incidente_id)
    
    # Formatear evidencias como diccionarios para asegurar serialization correcta
    evidencias_formateadas = []
    for e in evidencias:
        evidencias_formateadas.append({
            "id": e.id,
            "incidente_id": e.incidente_id,
            "tipo": e.tipo,
            "url_archivo": e.url_archivo,
            "contenido": e.contenido,
            "transcripcion": e.transcripcion,
            "descripcion": e.descripcion,
            "fecha_subida": e.fecha_subida.isoformat() if e.fecha_subida else None
        })
    
    # Formatear historial
    historial_formateado = []
    for h in historia:
        historial_formateado.append({
            "id": h.id,
            "incidente_id": h.incidente_id,
            "titulo": h.titulo,
            "descripcion": h.descripcion,
            "fecha_hora": h.fecha_hora.isoformat() if h.fecha_hora else None
        })
    
    return {
        "incidente": {
            "id": incidente.id,
            "cliente_id": incidente.cliente_id,
            "vehiculo_id": incidente.vehiculo_id,
            "especialidad_ia": incidente.especialidad_ia,
            "descripcion_ia": incidente.descripcion_ia,
            "prioridad": incidente.prioridad.value if incidente.prioridad else None,
            "estado": incidente.estado.value if incidente.estado else None,
            "descripcion_original": incidente.descripcion_original,
            "descripcion": incidente.descripcion,
            "requiere_mas_evidencia": incidente.requiere_mas_evidencia,
            "mensaje_solicitud": incidente.mensaje_solicitud,
            "ubicacion_lat": incidente.ubicacion_lat,
            "ubicacion_lng": incidente.ubicacion_lng,
            "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
            "fecha_actualizacion": incidente.fecha_actualizacion.isoformat() if incidente.fecha_actualizacion else None,
        },
        "evidencias": evidencias_formateadas,
        "historial": historial_formateado,
        "asignaciones": asignaciones,
        "total_evidencias": len(evidencias),
        "tiene_foto": any(e.tipo == "foto" for e in evidencias),
        "tiene_audio": any(e.tipo == "audio" for e in evidencias),
        "tiene_texto": any(e.tipo == "texto" for e in evidencias)
    }