from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from datetime import datetime

from app.db.database import get_db
from app.modulos.incidentes.services import evidencia as evidencia_service
from app.modulos.incidentes.services import incidente as incidente_service
from app.modulos.incidentes.services.cloudinary_service import cloudinary_service
from app.modulos.incidentes.schemas.evidencia import EvidenciaCreate, EvidenciaUpdate, EvidenciaResponse
from app.modulos.usuarios.models.usuario import Usuario
from app.core.security import get_current_user

router = APIRouter(prefix="/evidencias", tags=["evidencias"])


@router.get("/{incidente_id}", response_model=List[EvidenciaResponse])
def obtener_evidencias_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene las evidencias de un incidente"""
    return evidencia_service.obtener_evidencias_incidente(db, incidente_id)


@router.post("/{incidente_id}", response_model=EvidenciaResponse)
async def subir_evidencia(
    incidente_id: int,
    archivo: UploadFile = File(None),
    tipo: str = Form(...),
    contenido: str = Form(None),
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al subir archivo: {result.get('error')}"
            )
    
    evidencia_create = EvidenciaCreate(
        incidente_id=incidente_id,
        tipo=tipo,
        url_archivo=url_archivo,
        contenido=contenido_db
    )
    
    evidencia = evidencia_service.crear_evidencia(db, evidencia_create)
    
    return evidencia


@router.get("/incidente/{incidente_id}", response_model=List[EvidenciaResponse])
def obtener_evidencias_por_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    return evidencia_service.obtener_evidencias_incidente(db, incidente_id)


@router.get("/{evidencia_id}", response_model=EvidenciaResponse)
def obtener_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    evidencia = evidencia_service.obtener_evidencia(db, evidencia_id)
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    return evidencia


@router.put("/{evidencia_id}", response_model=EvidenciaResponse)
def actualizar_evidencia(
    evidencia_id: int,
    evidencia_update: EvidenciaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    evidencia = evidencia_service.actualizar_evidencia(db, evidencia_id, evidencia_update)
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    return evidencia


@router.delete("/{evidencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    success = evidencia_service.eliminar_evidencia(db, evidencia_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    return None