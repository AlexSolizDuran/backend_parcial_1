from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import asyncio
from pydantic import BaseModel
from fastapi import UploadFile, File, Form
from datetime import datetime
from pathlib import Path
from app.modulos.incidentes.services.cloudinary_service import cloudinary_service

from app.db.database import get_db
from app.modulos.incidentes.services import incidente as incidente_service
from app.modulos.incidentes.services.analisis_incidente import analisis_service
from app.modulos.incidentes.services.historia_incidente import cambiar_estado_incidente
from app.modulos.incidentes.services.notificacion import NotificacionService
from app.core.websocket.manager import ws_manager
from app.modulos.incidentes.schemas.incidente import (
    IncidenteCreate, IncidenteUpdate, IncidenteResponse
)
from app.modulos.incidentes.models.incidente import EstadoIncidente
from app.modulos.asignacion import service as asignacion_service
from app.modulos.asignacion.schema import AsignacionCreate as AsignacionCreateSchema, AsignacionResponse
from app.modulos.activos.models.historial_taller import HistorialTaller
from app.modulos.usuarios.models.usuario import Usuario
from app.core.security import get_current_user

router = APIRouter(tags=["incidentes"])


class EvidenciaRequest(BaseModel):
    tipo: str
    contenido: str = None


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
    
    from app.modulos.usuarios.services.notificacion import crear_notificacion
    from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
    
    crear_notificacion(db, NotificacionCreate(
        usuario_id=current_user.id,
        titulo="Emergencia creada",
        mensaje=f"Tu incidente #{db_incidente.id} ha sido reportado. Te informaremos cuando sea analizado.",
        tipo="incidente_creado"
    ))
    
    # NO Buscar talleres aquí - se hará después del análisis de IA
    # asyncio.create_task(
    #     NotificacionService.notificar_incidente_cercano(
    #         db=db,
    #         incidente_id=db_incidente.id,
    #         lat=db_incidente.ubicacion_lat,
    #         lng=db_incidente.ubicacion_lng,
    #         radio_km=10.0
    #     )
    # )
    
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


@router.get("/taller/{taller_id}", response_model=List[IncidenteResponse])
def obtener_incidentes_taller(
    taller_id: int,
    skip: int = 0,
    limit: int = 100,
    estado: str = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene los incidentes asignados a un taller"""
    from app.modulos.activos.models.taller import Taller

    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver estos incidentes")

    asignaciones = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.taller_id == taller_id,
        asignacion_service.Asignacion.estado.in_([
            asignacion_service.EstadoAsignacion.aceptada,
            asignacion_service.EstadoAsignacion.completada
        ])
    ).offset(skip).limit(limit).all()
    
    incidente_ids = list(set([a.incidente_id for a in asignaciones]))
    print(f"[DEBUG] Taller {taller_id} - Asignaciones: {len(asignaciones)}, IDs unicos: {incidente_ids}")
    
    if not incidente_ids:
        print("[DEBUG] No hay incidente_ids, retornando lista vacía")
        return []

    query = db.query(incidente_service.Incidente).filter(
        incidente_service.Incidente.id.in_(incidente_ids)
    ).distinct()

    if estado:
        query = query.filter(incidente_service.Incidente.estado == estado)

    incidentes = query.all()
    print(f"[DEBUG] Incidentes encontrados: {len(incidentes)} - IDs: {[i.id for i in incidentes]}")
    
    return incidentes


@router.get("/cercanos/{taller_id}", response_model=List[dict])
def obtener_incidentes_cercanos(
    taller_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene incidentes pendientes cercanos al taller para revisión"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.incidentes.services.incidente import buscar_talleres_cercanos

    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")

    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    talleres_cercanos = buscar_talleres_cercanos(
        db, taller.ubicacion_lat, taller.ubicacion_lng, radio_km=10.0
    )
    
    incidentes_pendientes = db.query(incidente_service.Incidente).filter(
        incidente_service.Incidente.estado == EstadoIncidente.reportado
    ).all()

    incidentes_cercanos = []
    for inc in incidentes_pendientes:
        if inc.ubicacion_lat and inc.ubicacion_lng:
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                return c * 6371
            
            distancia = haversine(
                taller.ubicacion_lng, taller.ubicacion_lat,
                inc.ubicacion_lng, inc.ubicacion_lat
            )
            
            if distancia <= 10.0:
                cliente = db.query(Usuario).filter(Usuario.id == inc.cliente_id).first()
                evidencias = db.query(incidente_service.Evidencia).filter(
                    incidente_service.Evidencia.incidente_id == inc.id
                ).all()
                
                incidentes_cercanos.append({
                    "id": inc.id,
                    "estado": inc.estado.value,
                    "especialidad_ia": inc.especialidad_ia,
                    "descripcion": inc.descripcion,
                    "descripcion_ia": inc.descripcion_ia,
                    "prioridad": inc.prioridad.value if inc.prioridad else None,
                    "ubicacion_lat": inc.ubicacion_lat,
                    "ubicacion_lng": inc.ubicacion_lng,
                    "distancia_km": round(distancia, 2),
                    "fecha_creacion": inc.fecha_creacion.isoformat() if inc.fecha_creacion else None,
                    "cliente": {
                        "id": cliente.id,
                        "nombre": cliente.nombre,
                        "telefono": cliente.telefono
                    } if cliente else None,
                    "total_evidencias": len(evidencias),
                    "evidencias": [{
                        "id": e.id,
                        "tipo": e.tipo,
                        "url_archivo": e.url_archivo,
                        "descripcion": e.descripcion
                    } for e in evidencias]
                })
    
    return sorted(incidentes_cercanos, key=lambda x: x['distancia_km'])


@router.get("/{incidente_id}/detalle-completo", response_model=dict)
def obtener_detalle_completo_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene detalles completos de un incidente con evidencias"""
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    cliente = db.query(Usuario).filter(Usuario.id == incidente.cliente_id).first()
    
    from app.modulos.incidentes.services import historia_incidente as historia_service
    from app.modulos.incidentes.models.evidencia import Evidencia
    from app.modulos.activos.models.vehiculo import Vehiculo
    
    evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()
    historial = historia_service.obtener_historia_incidente(db, incidente_id)
    vehiculo = None
    if incidente.vehiculo_id:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()

    return {
        "incidente": {
            "id": incidente.id,
            "estado": incidente.estado.value,
            "especialidad_ia": incidente.especialidad_ia,
            "descripcion_ia": incidente.descripcion_ia,
            "descripcion": incidente.descripcion,
            "descripcion_original": incidente.descripcion_original,
            "prioridad": incidente.prioridad.value if incidente.prioridad else None,
            "requiere_mas_evidencia": incidente.requiere_mas_evidencia,
            "mensaje_solicitud": incidente.mensaje_solicitud,
            "ubicacion_lat": incidente.ubicacion_lat,
            "ubicacion_lng": incidente.ubicacion_lng,
            "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
        },
        "cliente": {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "telefono": cliente.telefono,
            "email": cliente.email
        } if cliente else None,
        "vehiculo": {
            "id": vehiculo.id,
            "marca": vehiculo.marca,
            "modelo": vehiculo.modelo,
            "placa": vehiculo.placa,
            "color": vehiculo.color
        } if vehiculo else None,
        "evidencias": [{
            "id": e.id,
            "tipo": e.tipo,
            "url_archivo": e.url_archivo,
            "contenido": e.contenido,
            "transcripcion": e.transcripcion,
            "descripcion": e.descripcion,
            "fecha_subida": e.fecha_subida.isoformat() if e.fecha_subida else None
        } for e in evidencias],
        "historial": [{
            "id": h.id,
            "titulo": h.titulo,
            "descripcion": h.descripcion,
            "fecha_hora": h.fecha_hora.isoformat() if h.fecha_hora else None
        } for h in historial]
    }


@router.get("/incidente-en-curso", response_model=dict)
def obtener_incidente_en_curso(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el incidente en curso del cliente (asignado, en_camino, en_sitio)"""
    incidente = db.query(incidente_service.Incidente).filter(
        incidente_service.Incidente.cliente_id == current_user.id,
        incidente_service.Incidente.estado.in_([
            EstadoIncidente.asignado,
            EstadoIncidente.en_camino,
            EstadoIncidente.en_sitio
        ])
    ).first()
    
    if not incidente:
        return {"tiene_incidente": False}
    
    asignaciones = asignacion_service.obtener_asignaciones_por_incidente(db, incidente.id)
    
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
    
    from app.modulos.incidentes.services import historia_incidente as historia_service
    historia = historia_service.obtener_historia_incidente(db, incidente.id)
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

@router.get("/{incidente_id}/evidencias", response_model=List[dict])
def get_incidente_evidencias(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    from app.modulos.incidentes.services import evidencia as evidencia_service
    
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    evidencias = evidencia_service.obtener_evidencias_incidente(db, incidente_id)
    return [{
        "id": e.id,
        "tipo": e.tipo,
        "url_archivo": e.url_archivo,
        "contenido": e.contenido,
        "transcripcion": e.transcripcion,
        "descripcion": e.descripcion,
        "fecha_subida": e.fecha_subida.isoformat() if e.fecha_subida else None
    } for e in evidencias]


@router.post("/{incidente_id}/evidencias")
async def publicar_evidencia_incidente(
    incidente_id: int,
    tipo: str = Form(...),
    contenido: str = Form(None),
    archivo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Publica una nueva evidencia para un incidente"""
    from app.modulos.incidentes.services import evidencia as evidencia_service
    from app.modulos.incidentes.schemas.evidencia import EvidenciaCreate
    
    incidente = incidente_service.obtener_incidente(db, incidente_id)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    if current_user.id != incidente.cliente_id:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    url_archivo = None
    
    if archivo and tipo in ["foto", "audio"]:
        file_data = await archivo.read()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(archivo.filename).suffix if archivo.filename else ""
        filename = f"{incidente_id}_{timestamp}{file_extension}"
        
        if tipo == "foto":
            result = await cloudinary_service.upload_image(file_data, filename)
        else:
            result = await cloudinary_service.upload_audio(file_data, filename)
        
        if result.get("success"):
            url_archivo = result["url"]
        else:
            raise HTTPException(status_code=500, detail=f"Error al subir archivo a Cloudinary: {result.get('error')}")
    
    evidencia_data = EvidenciaCreate(
        incidente_id=incidente_id,
        tipo=tipo,
        contenido=contenido,
        url_archivo=url_archivo,
        transcripcion=None,
        descripcion=None
    )
    
    nueva_evidencia = evidencia_service.crear_evidencia(db, evidencia_data)
    
    return {
        "id": nueva_evidencia.id,
        "tipo": nueva_evidencia.tipo,
        "contenido": nueva_evidencia.contenido,
        "url_archivo": nueva_evidencia.url_archivo,
        "descripcion": nueva_evidencia.descripcion,
        "fecha_subida": nueva_evidencia.fecha_subida.isoformat() if nueva_evidencia.fecha_subida else None
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


@router.put("/{incidente_id}", response_model=IncidenteResponse)
def actualizar_incidente(
    incidente_id: int,
    incidente_update: IncidenteUpdate,
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
            detail="No tienes permiso para actualizar este incidente"
        )
    
    return incidente_service.actualizar_incidente(db, incidente_id, incidente_update)


@router.put("/{incidente_id}/analizar", response_model=IncidenteResponse)
async def analizar_incidente_con_ia(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Analyze all evidences of an incident using AI and create assignments"""
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
    
    analisis_fallido = (
        analisis_result.get("especialidad_ia") == "desconocido" or
        "Error" in analisis_result.get("descripcion_ia", "") or
        "Error" in analisis_result.get("descripcion", "") or
        analisis_result.get("requiere_mas_evidencia", 0) == 1
    )
    
    if analisis_fallido:
        nuevo_estado = EstadoIncidente.incluido
        
        cambiar_estado_incidente(
            db, incidente_id, nuevo_estado,
            notas=f"Análisis inconcluso: {analisis_result.get('descripcion', 'No se pudo completar el análisis automático')}"
        )
        
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Análisis no completado",
            mensaje="No pudimos analizar tu incidente automáticamente. Te contactaremos pronto para ayudarte.",
            tipo="analisis_fallido"
        ))
        
        resultado = incidente_service.actualizar_incidente(db, incidente_id, IncidenteUpdate(
            especialidad_ia=analisis_result["especialidad_ia"],
            descripcion_ia=analisis_result["descripcion_ia"],
            prioridad=analisis_result["prioridad"],
            descripcion=analisis_result["descripcion"],
            requiere_mas_evidencia=1,
            mensaje_solicitud=analisis_result.get("mensaje_solicitud") or "No se pudo completar el análisis automático",
            estado=nuevo_estado
        ))
        
        return resultado
    
    if analisis_result.get("requiere_mas_evidencia", 0) == 1:
        nuevo_estado = EstadoIncidente.reportado
        
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        mensaje_solicitud = analisis_result.get("mensaje_solicitud") or "Necesitamos más información sobre tu incidente"
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Información requerida",
            mensaje=mensaje_solicitud,
            tipo="requiere_mas_evidencia"
        ))
        
        from app.core.websocket.manager import ws_manager
        await ws_manager.send_to_cliente({
            "type": "requiere_mas_evidencia",
            "incidente_id": incidente_id,
            "mensaje": mensaje_solicitud,
            "mensaje_solicitud": mensaje_solicitud
        }, incidente.cliente_id)
    else:
        nuevo_estado = EstadoIncidente.reportado
    
    incidente_update = IncidenteUpdate(
        especialidad_ia=analisis_result["especialidad_ia"],
        descripcion_ia=analisis_result["descripcion_ia"],
        prioridad=analisis_result["prioridad"],
        descripcion=analisis_result["descripcion"],
        requiere_mas_evidencia=analisis_result.get("requiere_mas_evidencia", 0),
        mensaje_solicitud=analisis_result.get("mensaje_solicitud"),
        estado=nuevo_estado
    )
    
    resultado = incidente_service.actualizar_incidente(db, incidente_id, incidente_update)
    
    if analisis_result.get("especialidad_ia") and analisis_result.get("especialidad_ia") != "desconocido":
        from app.modulos.usuarios.services.notificacion import crear_notificacion
        from app.modulos.usuarios.schemas.notificacion import NotificacionCreate
        
        crear_notificacion(db, NotificacionCreate(
            usuario_id=incidente.cliente_id,
            titulo="Incidente analizado",
            mensaje=f"Tu incidente ha sido analizado. Especialidad: {analisis_result.get('especialidad_ia', 'General')}",
            tipo="analisis_ia_completo"
        ))
        
        await NotificacionService.notificar_analisis_completo(
            db=db,
            cliente_id=incidente.cliente_id,
            incidente_id=incidente_id,
            especialidad_ia=analisis_result.get("especialidad_ia", ""),
            prioridad=analisis_result.get("prioridad", ""),
            descripcion=analisis_result.get("descripcion", "")
        )
    
    if analisis_result.get("especialidad_ia") and analisis_result.get("especialidad_ia") != "desconocido" and analisis_result.get("requiere_mas_evidencia", 0) != 1:
        await NotificacionService.notificar_incidente_cercano(
            db=db,
            incidente_id=incidente_id,
            lat=resultado.ubicacion_lat,
            lng=resultado.ubicacion_lng,
            radio_km=10.0,
            especialidad=analisis_result["especialidad_ia"],
            prioridad=analisis_result["prioridad"]
        )
    
    return resultado


@router.post("/{incidente_id}/asignar", response_model=AsignacionResponse)
def asignar_incidente(
    incidente_id: int,
    asignacion: AsignacionCreateSchema,
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
    
    existing_asignaciones = asignacion_service.obtener_asignaciones_por_incidente(db, incidente_id)
    for asignacion_existente in existing_asignaciones:
        if asignacion_existente.taller_id == asignacion.taller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El incidente ya está asignado a este taller"
            )
    
    db_asignacion = asignacion_service.crear_asignacion(db, incidente_id, asignacion.taller_id)
    
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


@router.get("/taller/{taller_id}/asignados")
def obtener_incidentes_asignados(
    taller_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene incidentes asignados vigentes del taller (asignado, en_camino, en_sitio)"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.asignacion.model import EstadoAsignacion

    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    asignaciones = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.taller_id == taller_id,
        asignacion_service.Asignacion.estado.in_([
            EstadoAsignacion.aceptada, 
            EstadoAsignacion.completada
        ])
    ).all()
    
    processed_ids = set()
    estados_vigidos = [EstadoIncidente.asignado, EstadoIncidente.en_camino, EstadoIncidente.en_sitio]
    
    from datetime import datetime
    hoy = datetime.now().date()

    incidentes_result = []
    total_hoy = 0
    activos = 0
    finalizados = 0

    for asignacion in asignaciones:
        if asignacion.incidente_id in processed_ids:
            continue
        processed_ids.add(asignacion.incidente_id)
        
        incidente = db.query(incidente_service.Incidente).filter(
            incidente_service.Incidente.id == asignacion.incidente_id
        ).first()
        
        if not incidente:
            continue

        fecha_incidente = incidente.fecha_creacion.date() if incidente.fecha_creacion else None
        if fecha_incidente == hoy:
            total_hoy += 1
            if incidente.estado in [EstadoIncidente.asignado, EstadoIncidente.en_camino, EstadoIncidente.en_sitio]:
                activos += 1
            elif incidente.estado in [EstadoIncidente.finalizado, EstadoIncidente.cancelado]:
                finalizados += 1

        if incidente.estado in estados_vigidos:
            cliente = db.query(Usuario).filter(Usuario.id == incidente.cliente_id).first()
            vehiculo = None
            if incidente.vehiculo_id:
                from app.modulos.activos.models.vehiculo import Vehiculo
                vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()

            from app.modulos.incidentes.models.evidencia import Evidencia
            evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente.id).all()

            tecnico_info = None
            if asignacion.tecnico_id:
                tecnico = db.query(Tecnico).filter(Tecnico.id == asignacion.tecnico_id).first()
                if tecnico:
                    tecnico_usuario = db.query(Usuario).filter(Usuario.id == tecnico.usuario_id).first()
                    tecnico_info = {
                        "id": tecnico.id,
                        "nombre": tecnico_usuario.nombre if tecnico_usuario else "Técnico",
                        "telefono": tecnico_usuario.telefono if tecnico_usuario else None,
                        "disponible": tecnico.disponible,
                        "ubicacion_lat": tecnico.ubicacion_lat,
                        "ubicacion_lng": tecnico.ubicacion_lng
                    }

            asignacion_info = {
                "id": asignacion.id,
                "tecnico_id": asignacion.tecnico_id,
                "taller_id": asignacion.taller_id,
                "estado": asignacion.estado.value if hasattr(asignacion.estado, 'value') else str(asignacion.estado),
                "fecha_asignacion": asignacion.fecha_asignacion.isoformat() if asignacion.fecha_asignacion else None,
                "tecnico": tecnico_info
            }

            incidentes_result.append({
                "id": incidente.id,
                "estado": incidente.estado.value if hasattr(incidente.estado, 'value') else str(incidente.estado),
                "prioridad": incidente.prioridad.value if incidente.prioridad else None,
                "descripcion": incidente.descripcion,
                "descripcion_ia": incidente.descripcion_ia,
                "ubicacion_lat": incidente.ubicacion_lat,
                "ubicacion_lng": incidente.ubicacion_lng,
                "especialidad_ia": incidente.especialidad_ia,
                "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
                "fecha_actualizacion": incidente.fecha_actualizacion.isoformat() if incidente.fecha_actualizacion else None,
                "cliente": {
                    "id": cliente.id,
                    "nombre": cliente.nombre,
                    "telefono": cliente.telefono,
                    "email": cliente.email
                } if cliente else None,
"vehiculo": {
            "id": vehiculo.id,
            "marca": vehiculo.marca,
            "modelo": vehiculo.modelo,
            "placa": vehiculo.placa,
            "color": vehiculo.color
        } if vehiculo else None,
                "asignacion": asignacion_info,
                "total_evidencias": len(evidencias)
            })

    return {
        "total_hoy": total_hoy,
        "activos": activos,
        "finalizados": finalizados,
        "incidentes": sorted(incidentes_result, key=lambda x: x['fecha_creacion'] or '', reverse=True)
    }


@router.get("/taller/{taller_id}/estadisticas")
def obtener_estadisticas_taller(
    taller_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene estadísticas del taller: total, pendientes, completadas"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.asignacion.model import Asignacion, EstadoAsignacion
    
    taller = db.query(Taller).filter(Taller.id == taller_id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado")
    if taller.dueño_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    asignaciones = db.query(Asignacion).filter(
        Asignacion.taller_id == taller_id,
        Asignacion.estado.in_([EstadoAsignacion.aceptada, EstadoAsignacion.completada])
    ).all()
    
    processed_ids = set()
    total = 0
    pendientes = 0
    completadas = 0
    
    for asignacion in asignaciones:
        if asignacion.incidente_id in processed_ids:
            continue
        processed_ids.add(asignacion.incidente_id)
        
        incidente = db.query(incidente_service.Incidente).filter(
            incidente_service.Incidente.id == asignacion.incidente_id
        ).first()
        
        if not incidente:
            continue
        
        total += 1
        
        if incidente.estado in [EstadoIncidente.asignado, EstadoIncidente.en_camino, EstadoIncidente.en_sitio]:
            pendientes += 1
        elif incidente.estado == EstadoIncidente.finalizado:
            completadas += 1
    
    print(f"[DEBUG] Estadisticas taller {taller_id}: total={total}, pendientes={pendientes}, completadas={completadas}")
    
    return {
        "total": total,
        "pendientes": pendientes,
        "completadas": completadas
    }


@router.get("/{incidente_id}/detalle-asignado")
def obtener_detalle_asignado(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene detalle completo de un incidente asignado al taller - optimizado"""
    from app.modulos.activos.models.taller import Taller
    from app.modulos.usuarios.models.tecnico import Tecnico
    from app.modulos.incidentes.models.evidencia import Evidencia
    from app.modulos.incidentes.services import historia_incidente as historia_service
    from app.modulos.asignacion.model import EstadoAsignacion
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    incidente = db.query(incidente_service.Incidente).filter(
        incidente_service.Incidente.id == incidente_id
    ).first()
    
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    taller = db.query(Taller).filter(Taller.dueño_id == current_user.id).first()
    if not taller:
        raise HTTPException(status_code=404, detail="No tienes taller registrado")

    asignacion = db.query(asignacion_service.Asignacion).filter(
        asignacion_service.Asignacion.incidente_id == incidente_id,
        asignacion_service.Asignacion.taller_id == taller.id
    ).order_by(asignacion_service.Asignacion.fecha_asignacion.desc()).first()

    cliente = db.query(Usuario).filter(Usuario.id == incidente.cliente_id).first()

    vehiculo = None
    if incidente.vehiculo_id:
        from app.modulos.activos.models.vehiculo import Vehiculo
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == incidente.vehiculo_id).first()

    evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()
    
    historial = historia_service.obtener_historia_incidente(db, incidente_id)

    tecnico_info = None
    if asignacion and asignacion.tecnico_id:
        tecnico = db.query(Tecnico).filter(Tecnico.id == asignacion.tecnico_id).first()
        if tecnico:
            tecnico_usuario = db.query(Usuario).filter(Usuario.id == tecnico.usuario_id).first()
            tecnico_info = {
                "id": tecnico.id,
                "nombre": tecnico_usuario.nombre if tecnico_usuario else "Técnico",
                "telefono": tecnico_usuario.telefono if tecnico_usuario else None,
                "disponible": tecnico.disponible,
                "ubicacion_lat": tecnico.ubicacion_lat,
                "ubicacion_lng": tecnico.ubicacion_lng
            }

    return {
        "id": incidente.id,
        "estado": incidente.estado.value if hasattr(incidente.estado, 'value') else str(incidente.estado),
        "prioridad": incidente.prioridad.value if incidente.prioridad else None,
        "descripcion": incidente.descripcion,
        "descripcion_ia": incidente.descripcion_ia,
        "descripcion_original": incidente.descripcion_original,
        "especialidad_ia": incidente.especialidad_ia,
        "requiere_mas_evidencia": incidente.requiere_mas_evidencia,
        "mensaje_solicitud": incidente.mensaje_solicitud,
        "ubicacion_lat": incidente.ubicacion_lat,
        "ubicacion_lng": incidente.ubicacion_lng,
        "fecha_creacion": incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
        "cliente": {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "telefono": cliente.telefono,
            "email": cliente.email
        } if cliente else None,
        "vehiculo": {
            "id": vehiculo.id,
            "marca": vehiculo.marca,
            "modelo": vehiculo.modelo,
            "placa": vehiculo.placa,
            "color": vehiculo.color
        } if vehiculo else None,
        "tecnico": tecnico_info,
        "asignacion": {
            "id": asignacion.id,
            "tecnico_id": asignacion.tecnico_id,
            "taller_id": asignacion.taller_id,
            "estado": asignacion.estado.value if hasattr(asignacion.estado, 'value') else str(asignacion.estado),
            "fecha_asignacion": asignacion.fecha_asignacion.isoformat() if asignacion.fecha_asignacion else None,
        } if asignacion else None,
        "evidencias": [{
            "id": e.id,
            "tipo": e.tipo,
            "url_archivo": e.url_archivo,
            "contenido": e.contenido,
            "transcripcion": e.transcripcion,
            "descripcion": e.descripcion,
            "fecha_subida": e.fecha_subida.isoformat() if e.fecha_subida else None
        } for e in evidencias],
        "historial": [{
            "id": h.id,
            "titulo": h.titulo,
            "descripcion": h.descripcion,
            "fecha_hora": h.fecha_hora.isoformat() if h.fecha_hora else None
        } for h in historial]
    }
