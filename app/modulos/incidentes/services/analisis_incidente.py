from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from app.modulos.incidentes.models.evidencia import Evidencia
from app.modulos.incidentes.models.incidente import Incidente, PrioridadIncidente
from app.modulos.incidentes.services import incidente as incidente_service
from app.modulos.incidentes.services import evidencia as evidencia_service
from app.modulos.ia_core.services.openrouter_client import OpenRouterClient
import logging
import re

logger = logging.getLogger(__name__)

_http_client = None

def _get_httpx_client():
    global _http_client
    if _http_client is None:
        import httpx
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client

def _close_httpx_client():
    global _http_client
    if _http_client is not None:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_http_client.aclose())
            else:
                loop.run_until_complete(_http_client.aclose())
        except Exception as e:
            logger.error(f"Error closing httpx client: {e}")
        _http_client = None


class AnalisisIncidenteService:
    def __init__(self):
        self.openrouter_client = OpenRouterClient()

    async def analizar_evidencia(self, evidencia: Evidencia) -> Dict[str, Any]:
        """
        Analiza una evidencia individual según su tipo:
        - foto: analiza con visión AI
        - audio: transcribe con Whisper
        - texto: usa el contenido directamente
        """
        if evidencia.tipo == "foto":
            if evidencia.url_archivo:
                return await self._analizar_foto(evidencia.url_archivo)
            return {"descripcion": "No hay imagen disponible", "transcripcion": None}
        
        elif evidencia.tipo == "audio":
            if evidencia.url_archivo:
                transcripcion = await self._transcribir_audio(evidencia.url_archivo)
                return {"descripcion": transcripcion, "transcripcion": transcripcion}
            return {"descripcion": "No hay audio disponible", "transcripcion": None}
        
        elif evidencia.tipo == "texto":
            return {"descripcion": evidencia.contenido, "transcripcion": evidencia.contenido}
        
        return {"descripcion": "Tipo de evidencia desconocido", "transcripcion": None}

    async def _analizar_foto(self, image_url: str) -> Dict[str, Any]:
        """Analiza una imagen con el modelo de visión"""
        try:
            result = await self.openrouter_client.analyze_image(image_url)
            return {
                "descripcion": result.get("descripcion", "Descripción no disponible"),
                "transcripcion": result.get("descripcion", "Descripción no disponible")
            }
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"descripcion": "Error al analizar imagen", "transcripcion": None}

    async def _transcribir_audio(self, audio_url: str) -> str:
        """Transcribe un audio con Whisper"""
        try:
            transcripcion = await self.openrouter_client.transcribe_audio(audio_url)
            return transcripcion
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return "Error al transcribir audio"

    async def analizar_incidente_completo(self, db: Session, incidente_id: int) -> Dict[str, Any]:
        """
        Analiza todas las evidencias de un incidente y genera:
        - especialidad_ia
        - descripcion_ia
        - prioridad
        - descripcion
        """
        try:
            incidente = incidente_service.obtener_incidente(db, incidente_id)
            if not incidente:
                return {
                    "especialidad_ia": "desconocido",
                    "descripcion_ia": "Incidente no encontrado",
                    "prioridad": PrioridadIncidente.media,
                    "descripcion": "Error: incidente no encontrado"
                }

            evidencias = evidencia_service.obtener_evidencias_incidente(db, incidente_id)
            
            if not evidencias:
                return {
                    "especialidad_ia": "desconocido",
                    "descripcion_ia": "No hay evidencias para analizar",
                    "prioridad": PrioridadIncidente.media,
                    "descripcion": "No se han cargado evidencias (fotos, audio o texto)"
                }

            analisis_resultados = []
            transcripciones = []

            for evidencia in evidencias:
                resultado = await self.analizar_evidencia(evidencia)
                
                if resultado.get("descripcion"):
                    evidencia.descripcion = resultado["descripcion"]
                    db.commit()

                analisis_resultados.append({
                    "tipo": evidencia.tipo,
                    "descripcion": resultado.get("descripcion")
                })

                if resultado.get("transcripcion"):
                    transcripciones.append(resultado["transcripcion"])

            texto_combinado = "\n".join([
                f"[{a['tipo'].upper()}]: {a['descripcion']}" 
                for a in analisis_resultados
            ])

            return await self._analisis_final_ia(texto_combinado, db)
        except Exception as e:
            logger.error(f"Error en analizar_incidente_completo: {e}")
            return self._respuesta_default()

    async def _analisis_final_ia(self, texto_combinado: str, db: Session) -> Dict[str, Any]:
        """Envía todas las transcripciones a la IA para generar el análisis final"""
        try:
            from app.modulos.activos.services.especialidad import obtener_especialidades
            
            especialidades_db = obtener_especialidades(db)
            nombres_especialidades = [e.nombre for e in especialidades_db]
            especialidades_str = ", ".join(nombres_especialidades)

            prompt = f"""Eres un experto en diagnóstico de vehículos. Analiza las siguientes evidencias de un incidente vehicular y determina:

1. ESPECIALIDAD: Selecciona la especialidad más adecuada de esta lista: {especialidades_str}
2. DESCRIPCION_IA: Descripción técnica del problema detectado (máximo 100 palabras)
3. PRIORIDAD: Nivel de urgencia (baja, media, alta, urgente)
4. DESCRIPCION: Descripción clara y sencilla del problema para el usuario (máximo 50 palabras)
5. COHERENCIA: Evalúa si las evidencias (foto, audio, texto) son coherentes entre sí o si describen problemas diferentes. Responde "coherente" si todas apuntan a un mismo problema, o "incoherente" si son muy diferentes o contradictorias.
6. MENSAJE_SOLICITUD: Si las evidencias son incoherentes, genera un mensaje educado pidiendo al cliente que proporcione más detalles o nuevas evidencias que permitan entender mejor el problema.

Evidencias del incidente:
{texto_combinado}

Responde en formato JSON exactamente así:
{{
  "especialidad_ia": "especialidad seleccionada",
  "descripcion_ia": "descripción técnica",
  "prioridad": "baja|media|alta|urgente",
  "descripcion": "descripción clara",
  "coherencia": "coherente|incoherente",
  "mensaje_solicitud": "mensaje para solicitar más evidencia si es necesario"
}}"""

            client = _get_httpx_client()
            from app.core.config import settings
            
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o",
                    "messages": [
                        {"role": "system", "content": "Eres un experto en diagnóstico vehicular. Respondes siempre en JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis = eval(json_match.group())
                    
                    prioridad_map = {
                        "baja": PrioridadIncidente.baja,
                        "media": PrioridadIncidente.media,
                        "alta": PrioridadIncidente.alta,
                        "urgente": PrioridadIncidente.urgente
                    }
                    
                    coherencia = analysis.get("coherencia", "coherente")
                    
                    return {
                        "especialidad_ia": analysis.get("especialidad_ia", "desconocido"),
                        "descripcion_ia": analysis.get("descripcion_ia", "Descripción no disponible"),
                        "prioridad": prioridad_map.get(analysis.get("prioridad", "media").lower(), PrioridadIncidente.media),
                        "descripcion": analysis.get("descripcion", "Problema detectado en el vehículo"),
                        "requiere_mas_evidencia": 1 if coherencia.lower() == "incoherente" else 0,
                        "mensaje_solicitud": analysis.get("mensaje_solicitud") if coherencia.lower() == "incoherente" else None
                    }
            
            return self._respuesta_default()
                    
        except Exception as e:
            logger.error(f"Error in final analysis: {e}")
            return self._respuesta_default()

    def _respuesta_default(self) -> Dict[str, Any]:
        """Respuesta por defecto si falla el análisis"""
        return {
            "especialidad_ia": "desconocido",
            "descripcion_ia": "Error al analizar el incidente",
            "prioridad": PrioridadIncidente.media,
            "descripcion": "No se pudo completar el análisis automático. Contacte al taller manualmente.",
            "requiere_mas_evidencia": 0,
            "mensaje_solicitud": None
        }


analisis_service = AnalisisIncidenteService()

def close_analysis_client():
    """Cerrar el cliente HTTP compartido"""
    _close_httpx_client()