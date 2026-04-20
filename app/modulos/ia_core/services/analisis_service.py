from typing import Dict, Any, Optional
import logging
from app.modulos.ia_core.services.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class AnalisisIAService:
    def __init__(self):
        self.openrouter_client = OpenRouterClient()
    
    async def analizar_incidente_completo(
        self,
        evidencias: list,
        descripcion_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform complete AI analysis of an incident:
        1. Analyze images for mechanical failure classification
        2. Transcribe audio to text
        3. Combine all information to determine final priority
        
        Returns:
        {
            "especialidad_ia": str,
            "descripcion_ia": str,
            "prioridad_sugerida": str,
            "transcripcion_audio": Optional[str],
            "confianza": float
        }
        """
        try:
            # Initialize results
            especialidad_final = "desconocido"
            descripcion_final = "No se pudo realizar análisis"
            prioridad_sugerida = "media"
            transcripcion_audio = None
            confianzas = []
            
            # Process each evidence
            for evidencia in evidencias:
                if evidencia.tipo == "foto":
                    # Analyze image
                    resultado_imagen = await self.openrouter_client.analyze_image(
                        evidencia.url_archivo
                    )
                    
                    # Update with best result so far (simple approach: take first valid result)
                    if especialidad_final == "desconocido":
                        especialidad_final = resultado_imagen.get("categoria", "desconocido")
                        descripcion_final = resultado_imagen.get("descripcion", "No se pudo generar descripción")
                        confianzas.append(0.8)  # Placeholder confidence
                
                elif evidencia.tipo == "audio":
                    # Transcribe audio
                    transcripcion = await self.openrouter_client.transcribe_audio(
                        evidencia.url_archivo
                    )
                    transcripcion_audio = transcripcion
                    
                    # If we have transcription, analyze it for priority hints
                    if transcripcion and transcripcion != "Error al transcribir el audio":
                        prioridad_desde_texto = await self.openrouter_client.analyze_text_for_priority(
                            transcripcion, 
                            especialidad_final if especialidad_final != "desconocido" else ""
                        )
                        # We'll use this later to refine priority
            
            # If we have original description, also analyze it for priority
            if descripcion_original:
                prioridad_desde_descripcion = await self.openrouter_client.analyze_text_for_priority(
                    descripcion_original,
                    especialidad_final if especialidad_final != "desconocido" else ""
                )
                # We'll combine all priority signals
            
            # Determine final priority based on all available information
            # For now, we'll use a simple heuristic:
            # - If we have AI-suggested priority from image analysis, use it
            # - Otherwise, default based on category
            # TODO: Implement more sophisticated priority aggregation
            
            # Try to get priority from image analysis if available
            # This would need to be stored from the image analysis step
            # For now, we'll use a placeholder
            
            # Simple priority mapping based on category (can be improved)
            categoria_lower = especialidad_final.lower() if especialidad_final else ""
            if any(word in categoria_lower for word in ["freno", "direccion", "motor"]):
                prioridad_sugerida = "alta"
            elif any(word in categoria_lower for word in ["electrico", "luces"]):
                prioridad_sugerida = "media"
            else:
                prioridad_sugerida = "media"  # default
            
            # Override with description analysis if we have strong signals
            if descripcion_original:
                # Check for urgent keywords in description
                descripcion_lower = descripcion_original.lower()
                if any(word in descripcion_lower for word in ["fuego", "humo", "explosion", "liquido freno"]):
                    prioridad_sugerida = "urgente"
                elif any(word in descripcion_lower for word in ["freno", "direccion", "no frena"]):
                    prioridad_sugerida = "alta"
            
            return {
                "especialidad_ia": especialidad_final,
                "descripcion_ia": descripcion_final,
                "prioridad_sugerida": prioridad_sugerida,
                "transcripcion_audio": transcripcion_audio,
                "confianza": sum(confianzas) / len(confianzas) if confianzas else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error in complete incident analysis: {e}")
            return {
                "especialidad_ia": "error",
                "descripcion_ia": f"Error durante el análisis: {str(e)}",
                "prioridad_sugerida": "media",
                "transcripcion_audio": None,
                "confianza": 0.0
            }