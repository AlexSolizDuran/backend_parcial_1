from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.usuarios.schemas.tecnico import TecnicoResponse, TecnicoCreate
from app.modulos.usuarios.services import tecnico as tecnico_service
from app.modulos.usuarios.routers.usuario import get_current_user
from app.modulos.activos.models.taller import Taller
from app.modulos.incidentes.services.notificacion import NotificacionService

router = APIRouter(prefix="/tecnicos")

class tecnicoConTaller(BaseModel):
    disponible: bool = True
    usuario_id: int


@router.post("/", response_model=TecnicoResponse)
def crear_tecnico(
    tecnico: tecnicoConTaller,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueño pueden crear técnicos")
    
    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        raise HTTPException(status_code=400, detail="No tienes un taller registrado")
    
    if not tecnico.usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")
    
    db_tecnico = tecnico_service.asignar_taller(db, tecnico.usuario_id, taller.id, tecnico.disponible)
    if not db_tecnico:
        db_tecnico = tecnico_service.crear_tecnico_por_usuario_id(db, tecnico.usuario_id, taller.id, tecnico.disponible)
    return db_tecnico


@router.post("/registrar", response_model=TecnicoResponse)
def registrar_tecnico(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol != "tecnico":
        raise HTTPException(status_code=403, detail="Solo usuarios con rol tecnico pueden registrarse")
    
    db_tecnico = tecnico_service.crear_tecnico(db, current_user.id)
    if not db_tecnico:
        raise HTTPException(status_code=400, detail="Ya existe un tecnico para este usuario")
    return db_tecnico


def _obtener_historial_incidente(incidente_id: int, db: Session) -> list:
    """Obtiene el historial de un incidente"""
    from app.modulos.incidentes.models.historial import HistoriaIncidente
    historial = db.query(HistoriaIncidente).filter(
        HistoriaIncidente.incidente_id == incidente_id
    ).order_by(HistoriaIncidente.fecha_hora.asc()).all()
    return [
        {
            "id": h.id,
            "titulo": h.titulo,
            "descripcion": h.descripcion,
            "fecha_hora": h.fecha_hora.isoformat() if h.fecha_hora else None
        } for h in historial
    ]


@router.get("/mi-incidente", response_model=dict)
def get_mi_incidente(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el incidente asignado al técnico actual"""
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.asignacion import service as asignacion_service
    from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente
    from app.modulos.activos.models.vehiculo import Vehiculo
    from app.modulos.usuarios.models.usuario import Usuario as UsuarioModel
    from app.modulos.activos.models.taller import Taller

    logger.info(f"Mi incidente - usuario: {current_user.id}, email: {current_user.email}")
    
    db_tecnico = db.query(Tecnico).filter(Tecnico.usuario_id == current_user.id).first()
    if not db_tecnico:
        logger.error(f"Usuario {current_user.id} no es técnico")
        raise HTTPException(status_code=404, detail="No eres técnico")

    logger.info(f"Técnico encontrado: id={db_tecnico.id}, disponible={db_tecnico.disponible}")
    
    taller = None
    if db_tecnico.taller_id:
        taller = db.query(Taller).filter(Taller.id == db_tecnico.taller_id).first()

    asignacion = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.tecnico_id == db_tecnico.id,
        asignacion_service.Asignacion.estado.in_([
            asignacion_service.EstadoAsignacion.aceptada,
            asignacion_service.EstadoAsignacion.pendiente
        ])
    ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()

    if not asignacion:
        return {
            "tiene_incidente": False,
            "tecnico": {
                "id": db_tecnico.id,
                "disponible": db_tecnico.disponible,
                "nombre_taller": taller.nombre if taller else None,
                "taller_id": taller.id if taller else None,
                "ubicacion_lat": db_tecnico.ubicacion_lat,
                "ubicacion_lng": db_tecnico.ubicacion_lng,
                "usuario": {
                    "id": current_user.id,
                    "nombre": current_user.nombre,
                    "email": current_user.email,
                    "telefono": current_user.telefono,
                    "username": current_user.username
                }
            }
        }

    logger.info(f"Asignación encontrada: id={asignacion.id}, estado={asignacion.estado}")
    incidente = db.query(Incidente).filter(
        Incidente.id == asignacion.incidente_id,
        Incidente.estado.in_([
            EstadoIncidente.asignado,
            EstadoIncidente.en_camino,
            EstadoIncidente.en_sitio
        ])
    ).first()
    
    if not incidente:
        return {
            "tiene_incidente": False,
            "tecnico": {
                "id": db_tecnico.id,
                "disponible": db_tecnico.disponible,
                "nombre_taller": taller.nombre if taller else None,
                "taller_id": taller.id if taller else None,
                "usuario": {
                    "id": current_user.id,
                    "nombre": current_user.nombre,
                    "email": current_user.email,
                    "telefono": current_user.telefono,
                    "username": current_user.username
                }
            }
        }

    cliente = db.query(UsuarioModel).filter(UsuarioModel.id == incidente.cliente_id).first()

    vehiculo = None
    if incidente.vehiculo_id:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()

    return {
        "tiene_incidente": True,
        "tecnico": {
            "id": db_tecnico.id,
            "disponible": db_tecnico.disponible,
            "ubicacion_lat": db_tecnico.ubicacion_lat,
            "ubicacion_lng": db_tecnico.ubicacion_lng,
            "nombre_taller": taller.nombre if taller else None,
            "taller_id": taller.id if taller else None,
            "usuario": {
                "id": current_user.id,
                "nombre": current_user.nombre,
                "email": current_user.email,
                "telefono": current_user.telefono,
                "username": current_user.username
            }
        },
        "incidente": {
            "id": incidente.id,
            "estado": incidente.estado.value,
            "prioridad": incidente.prioridad.value if incidente.prioridad else None,
            "descripcion": incidente.descripcion_original,
            "descripcion": incidente.descripcion,
            "descripcion_ia": incidente.descripcion_ia,
            "ubicacion_lat": incidente.ubicacion_lat,
            "ubicacion_lng": incidente.ubicacion_lng,
            "direccion": None,
            "mensaje_solicitud": incidente.mensaje_solicitud,
            "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "email": cliente.email,
                "telefono": cliente.telefono
            } if cliente else None,
            "vehiculo": {
                "id": vehiculo.id,
                "marca": vehiculo.marca,
                "modelo": vehiculo.modelo,
                "patente": vehiculo.placa,
                "color": vehiculo.color,
            } if vehiculo else None,
            "evidencias": [
                {
                    "id": ev.id,
                    "tipo": ev.tipo,
                    "url_archivo": ev.url_archivo,
                    "contenido": ev.contenido,
                    "transcripcion": ev.transcripcion,
                    "descripcion": ev.descripcion,
                } for ev in incidente.evidencias
            ] if incidente.evidencias else [],
            "historial": _obtener_historial_incidente(incidente.id, db)
        }
    }


class ActualizarEstadoRequest(BaseModel):
    estado: str


class ActualizarUbicacionRequest(BaseModel):
    lat: float
    lng: float


@router.put("/{tecnico_id}/actualizar-estado", response_model=dict)
async def actualizar_estado_incidente(
    tecnico_id: int,
    request: ActualizarEstadoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza el estado del incidente asignado al técnico"""
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.asignacion import service as asignacion_service
    from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente
    from app.modulos.incidentes.services import historia_incidente as historia_service

    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    if db_tecnico.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar este incidente")

    asignacion = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.tecnico_id == db_tecnico.id,
        asignacion_service.Asignacion.estado == asignacion_service.EstadoAsignacion.aceptada
    ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="No tienes incidentes asignados")

    incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    nuevo_estado = request.estado
    titulo = ""
    descripcion = ""

    if nuevo_estado == "en_camino":
        nuevo_estado = EstadoIncidente.en_camino
        titulo = "Técnico en camino"
        descripcion = "El técnico se dirige al lugar del incidente"
    elif nuevo_estado == "en_sitio":
        nuevo_estado = EstadoIncidente.en_sitio
        titulo = "Técnico en sitio"
        descripcion = "El técnico ha llegado al lugar del incidente"
    elif nuevo_estado == "finalizado":
        nuevo_estado = EstadoIncidente.finalizado
        titulo = "Incidente finalizado"
        descripcion = "El incidente ha sido resuelto"
    else:
        raise HTTPException(status_code=400, detail="Estado inválido")

    incidente.estado = nuevo_estado
    db.commit()
    db.refresh(incidente)

    if titulo:
        db_historial = historia_service.HistoriaIncidente(
            incidente_id=incidente.id,
            titulo=titulo,
            descripcion=descripcion
        )
        db.add(db_historial)
        db.commit()
        
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        tipo_notificacion = f"incidente_{request.estado}"
        
        mensaje_cliente = descripcion
        titulo_notif = titulo
        
        if request.estado == "en_camino":
            titulo_notif = "Técnico en camino"
            mensaje_cliente = "El técnico se está dirigiendo a tu ubicación"
        elif request.estado == "en_sitio":
            titulo_notif = "Técnico llegó al lugar"
            mensaje_cliente = "El técnico ha llegado a tu ubicación"
        elif request.estado == "finalizado":
            titulo_notif = "Incidente resuelto"
            mensaje_cliente = "Tu incidente ha sido resuelto. ¡Gracias por usar AUXIA!"
        
        db.add(crear_notificacion(
            db, NotificacionCreate(
                usuario_id=incidente.cliente_id,
                titulo=titulo_notif,
                mensaje=mensaje_cliente,
                tipo=tipo_notificacion
            )
        ))
        db.commit()
        
        await NotificacionService.notificar_cambio_estado(
            incidente_id=incidente.id,
            cliente_id=incidente.cliente_id,
            nuevo_estado=request.estado,
            mensaje=mensaje_cliente
        )
        
    return {"message": "Estado actualizado", "nuevo_estado": incidente.estado.value}


class CancelarIncidenteRequest(BaseModel):
    motivo: str


@router.put("/{tecnico_id}/cancelar-incidente", response_model=dict)
def cancelar_incidente(
    tecnico_id: int,
    request: CancelarIncidenteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancela el incidente asignado al técnico"""
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.asignacion import service as asignacion_service
    from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente
    from app.modulos.incidentes.services import historia_incidente as historia_service

    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        raise HTTPException(status_code=404, detail=f"Técnico con ID {tecnico_id} no encontrado")

    if db_tecnico.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para cancelar este incidente")

    asignacion = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.tecnico_id == db_tecnico.id,
        asignacion_service.Asignacion.estado == asignacion_service.EstadoAsignacion.aceptada
    ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="No tienes ningún incidente asignado aceptar")

    incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    incidente.estado = EstadoIncidente.cancelado
    asignacion.estado = asignacion_service.EstadoAsignacion.rechazada
    db.commit()
    db.refresh(incidente)
    db.refresh(asignacion)

    db_historial = historia_service.HistoriaIncidente(
        incidente_id=incidente.id,
        titulo="Incidente cancelado",
        descripcion=f"Motivo: {request.motivo}"
    )
    db.add(db_historial)
    db.commit()

    from app.modulos.usuarios.services.notificacion import crear_notificacion
    from app.modulos.usuarios.schemas.notificacion import NotificacionCreate

    db.add(crear_notificacion(
        db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Incidente cancelado",
            mensaje=f"El incidente ha sido cancelado. Motivo: {request.motivo}",
            tipo="incidente_cancelado"
        )
    ))
    db.commit()

    return {"message": "Incidente cancelado", "estado": "cancelado"}


@router.put("/{tecnico_id}/ubicacion", response_model=dict)
def actualizar_ubicacion_tecnico(
    tecnico_id: int,
    request: ActualizarUbicacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza la ubicación del técnico"""
    from app.modulos.usuarios.models.tecnico import Tecnico

    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    if db_tecnico.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    db_tecnico.ubicacion_lat = request.lat
    db_tecnico.ubicacion_lng = request.lng
    db.commit()
    db.refresh(db_tecnico)

    return {"message": "Ubicación actualizada"}


@router.get("/historial", response_model=list)
def get_historial_tecnico(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el historial de incidentes atendidos por el técnico"""
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.asignacion import service as asignacion_service
    from app.modulos.incidentes.models.incidente import Incidente
    from app.modulos.activos.models.vehiculo import Vehiculo
    from app.modulos.usuarios.models.usuario import Usuario as UsuarioModel
    from app.modulos.activos.models.taller import Taller
    
    db_tecnico = db.query(Tecnico).filter(Tecnico.usuario_id == current_user.id).first()
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="No eres técnico")
    
    asignaciones = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.tecnico_id == db_tecnico.id
    ).offset(skip).limit(limit).all()
    
    historial = []
    for asignacion in asignaciones:
        incidente = db.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
        if incidente:
            vehiculo = None
            if incidente.vehiculo_id:
                vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()
            
            cliente = db.query(UsuarioModel).filter(UsuarioModel.id == incidente.cliente_id).first()
            
            taller = None
            if asignacion.taller_id:
                taller = db.query(Taller).filter(Taller.id == asignacion.taller_id).first()
            
            historial.append({
                "id": incidente.id,
                "estado": incidente.estado.value,
                "descripcion": incidente.descripcion,
                "ubicacion_lat": incidente.ubicacion_lat,
                "ubicacion_lng": incidente.ubicacion_lng,
            "direccion": None,
                "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
                "fecha_fin": asignacion.fecha_fin.isoformat() if asignacion.fecha_fin else None,
                "vehiculo": {
                    "marca": vehiculo.marca if vehiculo else None,
                    "modelo": vehiculo.modelo if vehiculo else None,
                    "patente": vehiculo.placa if vehiculo else None,
                } if vehiculo else None,
                "cliente": {
                    "nombre": cliente.nombre if cliente else None,
                    "telefono": cliente.telefono if cliente else None,
                } if cliente else None,
                "taller": {
                    "nombre": taller.nombre if taller else None,
                } if taller else None,
            })
    
    return historial


@router.get("/", response_model=list[TecnicoResponse])
def get_tecnicos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.rol != "dueno":
        raise HTTPException(status_code=403, detail="Solo dueños pueden ver técnicos")
    
    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        return []
    
    return tecnico_service.obtener_tecnicos_por_taller(db, taller.id)


@router.get("/disponibles/", response_model=list[TecnicoResponse])
def get_tecnicos_disponibles(taller_id: int = None, db: Session = Depends(get_db)):
    return tecnico_service.obtener_tecnicos_disponibles(db, taller_id)


@router.get("/taller/{taller_id}", response_model=list[TecnicoResponse])
def get_tecnicos_por_taller(
    taller_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los técnicos de un taller específico"""
    from app.modulos.activos.models.taller import Taller
    
    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    return tecnico_service.obtener_tecnicos_por_taller(db, taller_id)


@router.get("/taller/{taller_id}/disponibles", response_model=list[TecnicoResponse])
def get_tecnicos_disponibles_por_taller(
    taller_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene técnicos disponibles de un taller específico"""
    from app.modulos.activos.models.taller import Taller
    
    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    return tecnico_service.obtener_tecnicos_disponibles(db, taller_id)


@router.get("/{tecnico_id}", response_model=TecnicoResponse)
def get_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    db_tecnico = tecnico_service.obtener_tecnico(db, tecnico_id)
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")
    return db_tecnico


class DisponibilidadRequest(BaseModel):
    disponible: bool
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None


@router.put("/{tecnico_id}/disponibilidad", response_model=TecnicoResponse)
def update_disponibilidad(
    tecnico_id: int,
    request: DisponibilidadRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza disponibilidad y opcionalmente ubicación del técnico"""
    from app.modulos.usuarios.models.tecnico import Tecnico
    
    logger.info(f"=== UPDATE DISPONIBILIDAD ===")
    logger.info(f"tecnico_id: {tecnico_id}, disponible: {request.disponible}")
    logger.info(f"ubicacion_lat: {request.ubicacion_lat} (type: {type(request.ubicacion_lat)})")
    logger.info(f"ubicacion_lng: {request.ubicacion_lng} (type: {type(request.ubicacion_lng)})")
    logger.info(f"current_user.id: {current_user.id}")
    
    db_tecnico = db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()
    if not db_tecnico:
        logger.error(f"Técnico no encontrado: {tecnico_id}")
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    
    if db_tecnico.usuario_id != current_user.id:
        logger.error(f"Usuario {current_user.id} no tiene permiso para técnico {tecnico_id}")
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    logger.info(f"Antes - disponible: {db_tecnico.disponible}, lat: {db_tecnico.ubicacion_lat}, lng: {db_tecnico.ubicacion_lng}")
    
    db_tecnico.disponible = request.disponible
    
    if request.ubicacion_lat is not None and request.ubicacion_lng is not None:
        db_tecnico.ubicacion_lat = float(request.ubicacion_lat)
        db_tecnico.ubicacion_lng = float(request.ubicacion_lng)
        logger.info(f"Ubicación actualizada a: lat={db_tecnico.ubicacion_lat}, lng={db_tecnico.ubicacion_lng}")
    
    db.commit()
    db.refresh(db_tecnico)
    logger.info(f"Después - disponible: {db_tecnico.disponible}, lat: {db_tecnico.ubicacion_lat}, lng: {db_tecnico.ubicacion_lng}")
    
    return db_tecnico


@router.delete("/{tecnico_id}")
def delete_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    db_tecnico = tecnico_service.eliminar_tecnico(db, tecnico_id)
    if not db_tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")
    return {"message": "Tecnico eliminado"}
