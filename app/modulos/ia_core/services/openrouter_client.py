import httpx
import json
import logging
import base64
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://auxia.app",  # Optional, for OpenRouter stats
            "X-Title": "Auxia Emergency Response"  # Optional, for OpenRouter stats
        }
    
    async def analyze_image(self, image_url: str, model: str = "openai/gpt-4o") -> Dict[str, Any]:
        """
        Analyze an image using OpenRouter's vision models
        Returns analysis results including category, description, and priority suggestion
        """
        try:
            # First verify the image URL is accessible
            async with httpx.AsyncClient() as client:
                img_check = await client.head(image_url, timeout=5.0)
                if img_check.status_code != 200:
                    logger.error(f"Image URL not accessible: {image_url} - Status: {img_check.status_code}")
                    return {
                        "categoria": "desconocido",
                        "descripcion": "Error: La imagen no está accesible públicamente",
                        "prioridad_sugerida": "media"
                    }
            
            # Call OpenRouter API with improved prompt
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Eres un experto en mecánica automotriz. Analizas imágenes de vehículos y determinas fallas mecánicas."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": """Analiza esta imagen de un incidente vehicular o problema mecánico.

Proporciona:
1. Categoría de la falla mecánica (ej. frenos, motor, eléctrico, transmisión, suspensión, llantas, carrocería, otros)
2. Descripción detallada de lo que observas en la imagen
3. Nivel de prioridad sugerido basado en implicaciones de seguridad:
   - baja: Problema menor, no afecta la seguridad inmediata
   - media: Problema que debe atenderse pronto pero no es urgente
   - alta: Problema que afecta la seguridad y requiere atención inmediata
   - urgente: Problema crítico que representa peligro inminente

Responde ÚNICAMENTE en formato JSON válido con estas claves exactas:
{
  "categoria": "categoría_detectada",
  "descripcion": "descripción detallada",
  "prioridad_sugerida": "baja|media|alta|urgente"
}"""
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_url
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    return {
                        "categoria": "desconocido",
                        "descripcion": "Error al analizar la imagen",
                        "prioridad_sugerida": "media"
                    }
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON from the response
                try:
                    # First try direct JSON parsing (works when response_format is used)
                    analysis = json.loads(content)
                    return {
                        "categoria": analysis.get("categoria", "desconocido"),
                        "descripcion": analysis.get("descripcion", "No se pudo generar descripción"),
                        "prioridad_sugerida": analysis.get("prioridad_sugerida", "media")
                    }
                except json.JSONDecodeError:
                    # Fallback to regex extraction if direct parsing fails
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            analysis = json.loads(json_match.group())
                            return {
                                "categoria": analysis.get("categoria", "desconocido"),
                                "descripcion": analysis.get("descripcion", "No se pudo generar descripción"),
                                "prioridad_sugerida": analysis.get("prioridad_sugerida", "media")
                            }
                        except:
                            pass
                    
                    # If all else fails, use the content as description
                    logger.warning(f"Could not parse JSON from image analysis: {content}")
                    return {
                        "categoria": "desconocido",
                        "descripcion": content[:500] if content else "No se pudo generar descripción",
                        "prioridad_sugerida": "media"
                    }
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return {
                "categoria": "desconocido",
                "descripcion": "Error de conexión con servicio de IA",
                "prioridad_sugerida": "media"
            }
    
async def transcribe_audio(self, audio_url: str, model: str = "openai/gpt-4o-audio-preview") -> str:
    """
    Transcribe audio using OpenRouter's audio-capable models via chat completions endpoint
    Returns transcribed text
    """
    try:
        # 1. Download audio from URL
        async with httpx.AsyncClient() as client:
            audio_response = await client.get(audio_url)
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio from {audio_url}: {audio_response.status_code}")
                return "Error al descargar el audio"
            audio_data = audio_response.content
        
        # 2. Detect audio format from URL extension
        import os
        file_ext = os.path.splitext(audio_url)[1].lower().lstrip('.')
        format_map = {
            'm4a': 'm4a', 'mp3': 'mp3', 'wav': 'wav', 
            'ogg': 'ogg', 'flac': 'flac', 'aac': 'aac'
        }
        audio_format = format_map.get(file_ext, 'm4a')
        
        # 3. Base64 encode audio
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 4. Call OpenRouter chat completions endpoint with audio input
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_base64,
                                        "format": audio_format
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "Transcribe el audio exactamente como se habla, sin añadir comentarios adicionales."
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1000
                }
            )
        
        if response.status_code != 200:
            logger.error(f"OpenRouter transcription error: {response.status_code} - {response.text}")
            return "Error al transcribir el audio"
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else "No se pudo transcribir el audio"
                
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}")
        return "Error de conexión con servicio de transcripción"
    
    async def analyze_text_for_priority(self, text: str, categoria: str = "") -> str:
        """
        Analyze text (from voice transcription or description) to suggest priority level
        Returns priority level: baja, media, alta, urgente
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "openai/gpt-4o",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Eres un experto en priorización de incidentes mecánicos. Analiza el texto y determina el nivel de prioridad basado en riesgo de seguridad."
                            },
                            {
                                "role": "user",
                                "content": f"""Analiza el siguiente reporte de incidente vehicular y determina el nivel de prioridad:
                                
                                Categoría de falla: {categoria}
                                Descripción: {text}
                                
                                Niveles de prioridad:
                - baja: Problema menor que no afecta la seguridad inmediata
                - media: Problema que debería atenderse pronto pero no es urgente
                - alta: Problema que afecta la seguridad y requiere atención inmediata
                - urgente: Problema crítico que representa peligro inminente
                
                                Responde SOLO con el nivel de prioridad: baja, media, alta o urgente"""
                            }
                        ],
                        "max_tokens": 10
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter text analysis API error: {response.status_code} - {response.text}")
                    return "media"
                
                result = response.json()
                priority = result["choices"][0]["message"]["content"].strip().lower()
                
                # Validate the response
                if priority in ["baja", "media", "alta", "urgente"]:
                    return priority
                else:
                    # Default to media if response is invalid
                    return "media"
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter text analysis API: {e}")
            return "media"