import cloudinary
import cloudinary.uploader
from typing import Dict, Any
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)


class CloudinaryService:
    """Service for uploading files to Cloudinary"""
    
    @staticmethod
    async def upload_image(file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Sube una imagen a Cloudinary y retorna la URL pública
        """
        try:
            result = cloudinary.uploader.upload(
                file_data,
                folder="auxia/evidencias/fotos",
                public_id=f"incidente_{filename}",
                resource_type="image"
            )
            return {
                "success": True,
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
        except Exception as e:
            logger.error(f"Error uploading image to Cloudinary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def upload_audio(file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Sube un audio a Cloudinary y retorna la URL pública
        """
        try:
            result = cloudinary.uploader.upload(
                file_data,
                folder="auxia/evidencias/audio",
                public_id=f"incidente_{filename}",
                resource_type="video"  # Cloudinary usa "video" para audio también
            )
            return {
                "success": True,
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
        except Exception as e:
            logger.error(f"Error uploading audio to Cloudinary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def upload_file(file_data: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Sube un archivo a Cloudinary según su tipo
        """
        if file_type in ["jpg", "jpeg", "png", "gif", "webp"]:
            return await CloudinaryService.upload_image(file_data, filename)
        elif file_type in ["mp3", "wav", "m4a", "ogg", "webm"]:
            return await CloudinaryService.upload_audio(file_data, filename)
        else:
            return {
                "success": False,
                "error": f"Tipo de archivo no soportado: {file_type}"
            }
    
    @staticmethod
    async def delete_file(public_id: str) -> Dict[str, Any]:
        """
        Elimina un archivo de Cloudinary
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error deleting file from Cloudinary: {e}")
            return {
                "success": False,
                "error": str(e)
            }


cloudinary_service = CloudinaryService()