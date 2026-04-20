import httpx
import json
import logging
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
    
    async def analyze_image(self, image_url: str, model: str = "qwen/qwen-2-vl-72b-instruct") -> Dict[str, Any]:
        """
        Analyze an image using OpenRouter's vision models
        Returns analysis results including category, description, and priority suggestion
        """
        try:
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
                                        "type": "text",
                                        "text": """Analyze this image of a vehicle incident or mechanical problem. 
                                        Provide:
                                        1. Category of mechanical failure (e.g., brakes, engine, electrical, transmission, suspension, tires)
                                        2. Detailed description of what you observe
                                        3. Suggested priority level (low, medium, high, urgent) based on safety implications
                                        
                                        Respond in JSON format with keys: categoria, descripcion, prioridad_sugerida"""
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
                        "max_tokens": 1000
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
                
                # Try to parse JSON from the response
                try:
                    # Extract JSON from the response if it's wrapped in text
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        return {
                            "categoria": analysis.get("categoria", "desconocido"),
                            "descripcion": analysis.get("descripcion", "No se pudo generar descripción"),
                            "prioridad_sugerida": analysis.get("prioridad_sugerida", "media")
                        }
                    else:
                        # Fallback if no JSON found
                        return {
                            "categoria": "desconocido",
                            "descripcion": content[:500] if content else "No se pudo generar descripción",
                            "prioridad_sugerida": "media"
                        }
                except Exception as e:
                    logger.error(f"Error parsing AI response: {e}")
                    return {
                        "categoria": "desconocido",
                        "descripcion": content[:500] if content else "Error al procesar respuesta",
                        "prioridad_sugerida": "media"
                    }
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return {
                "categoria": "desconocido",
                "descripcion": "Error de conexión con servicio de IA",
                "prioridad_sugerida": "media"
            }
    
    async def transcribe_audio(self, audio_url: str, model: str = "whisper-1") -> str:
        """
        Transcribe audio using OpenRouter's Whisper model
        Returns transcribed text
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=self.headers,
                    data={
                        "model": model,
                        "url": audio_url
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter Whisper API error: {response.status_code} - {response.text}")
                    return "Error al transcribir el audio"
                
                result = response.json()
                return result.get("text", "No se pudo transcribir el audio")
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter Whisper API: {e}")
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