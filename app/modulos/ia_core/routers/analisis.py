from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.modulos.incidentes.models.incidente import Incidente
from app.modulos.incidentes.models.evidencia import Evidencia
from app.modulos.incidentes.schemas.incidente import IncidenteUpdate
from app.modulos.ia_core.services.analisis_service import AnalisisIAService
from app.modulos.usuarios.models.usuario import Usuario
from app.core.security import get_current_user as get_current_user_dep

router = APIRouter(prefix="/ia", tags=["inteligencia-artificial"])

# Initialize service
analisis_service = AnalisisIAService()


@router.post("/analizar-incidente/{incidente_id}", response_model=IncidenteUpdate)
async def analizar_incidente(
    incidente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user_dep)
):
    """
    Perform AI analysis on an incident's evidence:
    - Analyze images for mechanical failure classification
    - Transcribe audio to text
    - Determine suggested priority level
    
    Returns the analysis results to update the incident record
    """
    # Get the incident
    incidente = db.query(Incidente).filter(Incidente.id == incidente_id).first()
    if not incidente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente no encontrado"
        )
    
    # Check permissions (client who reported it or workshop owner)
    if current_user.id != incidente.cliente_id and current_user.rol.value != "dueno":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para analizar este incidente"
        )
    
    # Get all evidence for this incident
    evidencias = db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()
    
    if not evidencias:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay evidencias para analizar en este incidente"
        )
    
    # Perform AI analysis
    resultado = await analisis_service.analizar_incidente_completo(
        evidencias=evidencias,
        descripcion_original=incidente.descripcion_original
    )
    
    # Return the update data
    return IncidenteUpdate(
        especialidad_ia=resultado["especialidad_ia"],
        descripcion_ia=resultado["descripcion_ia"],
        descripcion=resultado["descripcion"],
        prioridad=resultado["prioridad_sugerida"]  # This will be validated by the schema
    )


@router.post("/transcribir-audio", response_model=dict)
async def transcribir_audio(
    audio_url: str,
    current_user: Usuario = Depends(get_current_user_dep)
):
    """
    Transcribe audio to text using Whisper via OpenRouter
    """
    # In a real implementation, you might want to restrict this to authenticated users only
    # For now, we'll check authentication but allow the service to be called
    
    # Transcribe audio
    transcripcion = await analisis_service.openrouter_client.transcribe_audio(audio_url)
    
    return {
        "transcripcion": transcripcion,
        "audio_url": audio_url
    }


@router.post("/analizar-imagen", response_model=dict)
async def analizar_imagen(
    image_url: str,
    current_user: Usuario = Depends(get_current_user_dep)
):
    """
    Analyze image using vision model via OpenRouter
    """
    # Analyze image
    resultado = await analisis_service.openrouter_client.analyze_image(image_url)
    
    return {
        "categoria": resultado["categoria"],
        "descripcion": resultado["descripcion"],
        "prioridad_sugerida": resultado["prioridad_sugerida"],
        "image_url": image_url
    }