from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
from pathlib import Path
from datetime import datetime
import asyncio

from app.db.database import get_db
from app.modulos.incidentes.services import incidente as incidente_service
from app.modulos.incidentes.services.analisis_incidente import analisis_service
from app.modulos.incidentes.services.notificacion import NotificacionService
from app.modulos.incidentes.services.cloudinary_service import cloudinary_service
from app.modulos.incidentes.schemas.incidente import (
    IncidenteCreate, IncidenteUpdate, IncidenteResponse,
    EvidenciaCreate, EvidenciaResponse,
    AsignacionCreate, AsignacionResponse,
    HistoriaIncidenteResponse, HistoriaIncidenteCreate
)
from app.modulos.incidentes.models.incidente import Incidente, EstadoIncidente, PrioridadIncidente
from app.modulos.activos.models.historial_taller import HistorialTaller
from app.modulos.usuarios.models.usuario import Usuario
from app.core.security import get_current_user

router = APIRouter(prefix="/incidentes", tags=["incidentes"])


@router.post("/", response_model=IncidenteResponse)
async def crear_incidente(
    incidente: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.id != incidente.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para crear un incidente para otro usuario"
        )
    
    db_incidente = incidente_service.crear_incidente(db, incidente)
    
    asyncio.create_task(
        NotificacionService.notificar_incidente_cercano(
            db=db,
            incidente_id=db_incidente.id,
            lat=db_incidente.ubicacion_lat,
            lng=db_incidente.ubicacion_lng,
            radio_km=10.0
        )
    )
    
    return db_incidente


@router.get("/mis-incidentes", response_model=List[IncidenteResponse])
def obtener_mis_incidentes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidentes = incidente_service.obtener_incidentes_cliente(
        db, current_user.id, skip=skip, limit=limit
    )
    return incidentes


@router.get("/incidente-en-curso", response_model=Dict)
def obtener_incidente_en_curso(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el incidente en curso del cliente (asignado, en_camino, en_sitio)"""
    from app.modulos.incidentes.models.incidente import EstadoIncidente
    
    incidente = db.query(Incidente).filter(
        Incidente.cliente_id == current_user.id,
        Incidente.estado.in_([
            EstadoIncidente.asignado,
            EstadoIncidente.en_camino,
            EstadoIncidente.en_sitio
        ])
    ).first()
    
    if not incidente:
        return {"tiene_incidente": False}
    
    # Obtener asignaciones
    asignaciones = incidente_service.obtener_asignaciones_incidente(db, incidente.id)
    
    # Obtener información del técnico si hay asignación aceptada
    tecnico_info = None
    taller_info = None
    if asignaciones:
        asignacion = asignaciones[0]
        if asignacion.tecnico_id:
            from app.modulos.usuarios.models.tecnico import Tecnico
            tecnico = db.query(Tecnico).filter(Tecnico.id == asignacion.tecnico_id).first()
            if tecnico:
                tecnico_info = {
                    "id": tecnico.id,
                    "nombre": tecnico.usuario.nombre if tecnico.usuario else "Técnico",
                    "telefono": tecnico.usuario.telefono if tecnico.usuario else None,
                    "ubicacion_lat": tecnico.ubicacion_lat,
                    "ubicacion_lng": tecnico.ubicacion_lng,
                }
        if asignacion.taller:
            taller_info = {
                "id": asignacion.taller.id,
                "nombre": asignacion.taller.nombre,
                "telefono": asignacion.taller.telefono,
            }
    
    # Obtener historia del incidente
    historia = incidente_service.obtener_historia_incidente(db, incidente.id)
    historia_list = [
        {
            "id": h.id,
            "titulo": h.titulo,
            "descripcion": h.descripcion,
            "fecha_hora": h.fecha_hora.isoformat() if h.fecha_hora else None
        }
        for h in historia
    ]
    
    return {
        "tiene_incidente": True,
        "incidente": {
            "id": incidente.id,
            "estado": incidente.estado.value,
            "prioridad": incidente.prioridad.value if incidente.prioridad else None,
            "especialidad_ia": incidente.especialidad_ia,
            "descripcion": incidente.descripcion,
            "ubicacion_lat": incidente.ubicacion_lat,
            "ubicacion_lng": incidente.ubicacion_lng,
            "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
        },
        "taller": taller_info,
        "tecnico": tecnico_info,
        "historial": historia_list
    }


@router.get("/{incidente_id}", response_model=IncidenteResponse)
def obtener_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este incidente"
        )
    
    return incidente


@router.post("/{incidente_id}/evidencias", response_model=EvidenciaResponse)
async def subir_evidencia(
    incidente_id: int,
    archivo: UploadFile = File(None),
    tipo: str = ...,
    contenido: str = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Upload evidence (photo, audio, or text) for an incident"""
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para agregar evidencias a este incidente"
        )
    
    if tipo not in ["foto", "audio", "texto"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de evidencia debe ser 'foto', 'audio' o 'texto'"
        )
    
    url_archivo = None
    contenido_db = contenido
    
    if tipo == "texto":
        if not contenido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contenido es requerido para evidencias de tipo texto"
            )
    else:
        if not archivo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo es requerido para evidencias de tipo foto o audio"
            )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(archivo.filename).suffix if archivo.filename else ""
        filename = f"{incidente_id}_{timestamp}{file_extension}"
        
        file_data = await archivo.read()
        
        if tipo == "foto":
            result = await cloudinary_service.upload_image(file_data, filename)
        else:
            result = await cloudinary_service.upload_audio(file_data, filename)
        
        if result.get("success"):
            url_archivo = result["url"]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_BAD_REQUEST,
                detail=f"Error al subir archivo: {result.get('error')}"
            )
    
    evidencia_create = EvidenciaCreate(
        incidente_id=incidente_id,
        tipo=tipo,
        url_archivo=url_archivo,
        contenido=contenido_db
    )
    
    evidencia = incidente_service.agregar_evidencia(db, evidencia_create)
    
    return evidencia


@router.post("/{incidente_id}/analizar", response_model=IncidenteResponse)
async def analizar_incidente_con_ia(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Analyze all evidences of an incident using AI"""
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para analizar este incidente"
        )
    
    analisis_result = await analisis_service.analizar_incidente_completo(db, incidente_id)
    
    # Convertir requiere_mas_evidencia a booleano para el enum de estado
    if analisis_result.get("requiere_mas_evidencia", 0) == 1:
        nuevo_estado = EstadoIncidente.reportado  # Se queda en reportado para que pueda agregar más evidencias
    else:
        nuevo_estado = None
    
    incidente_update = IncidenteUpdate(
        especialidad_ia=analisis_result["especialidad_ia"],
        descripcion_ia=analisis_result["descripcion_ia"],
        prioridad=analisis_result["prioridad"],
        descripcion=analisis_result["descripcion"],
        requiere_mas_evidencia=analisis_result.get("requiere_mas_evidencia", 0),
        mensaje_solicitud=analisis_result.get("mensaje_solicitud"),
        estado=nuevo_estado
    )
    
    return incidente_service.actualizar_incidente(db, incidente_id, incidente_update)


@router.post("/{incidente_id}/asignar", response_model=AsignacionResponse)
def asignar_incidente(
    incidente_id: int,
    asignacion: AsignacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los dueños de talleres pueden asignar incidentes"
        )
    
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    existing_asignaciones = incidente_service.obtener_asignaciones_incidente(db, incidente_id)
    for asignacion_existente in existing_asignaciones:
        if asignacion_existente.taller_id == asignacion.taller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El incidente ya está asignado a este taller"
            )
    
    db_asignacion = incidente_service.crear_asignacion(db, incidente_id, asignacion.taller_id)
    
    incidente_service.cambiar_estado_incidente(
        db, incidente_id, EstadoIncidente.asignado,
        notas=f"Asignado a taller {asignacion.taller_id}"
    )
    
    db_historial = HistorialTaller(
        taller_id=asignacion.taller_id,
        titulo="Incidente asignado",
        descripcion=f"Se ha aceptado el incidente #{incidente_id}",
        tipo="incidente_aceptado"
    )
    db.add(db_historial)
    db.commit()
    
    return db_asignacion


@router.get("/{incidente_id}/historia", response_model=List[HistoriaIncidenteResponse])
def obtener_historia_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver la historia de este incidente"
        )
    
    historia = incidente_service.obtener_historia_incidente(db, incidente_id)
    return historia


@router.post("/{incidente_id}/historia", response_model=HistoriaIncidenteResponse)
def crear_historia_incidente(
    incidente_id: int,
    historia: HistoriaIncidenteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para agregar historia a este incidente"
        )
    
    return incidente_service.crear_historia_incidente(db, incidente_id, historia)


@router.get("/{incidente_id}/estadisticas")
def obtener_estadisticas_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver las estadísticas de este incidente"
        )
    
    return incidente_service.obtener_estadisticas_incidente(db, incidente_id)