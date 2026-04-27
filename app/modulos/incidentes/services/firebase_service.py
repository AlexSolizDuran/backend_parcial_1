import logging
from typing import Optional
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_initialized = False

def init_firebase(credentials_path: str = "firebase-credentials.json"):
    """Inicializa Firebase Admin SDK con las credenciales"""
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
    
    try:
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK inicializado correctamente")
        return True
    except FileNotFoundError:
        logger.error(f"Archivo de credenciales no encontrado: {credentials_path}")
        logger.warning("Las notificaciones push no funcionarán hasta configurar las credenciales de Firebase")
        return False
    except Exception as e:
        logger.error(f"Error al inicializar Firebase: {e}")
        return False


def send_push_notification(
    token_fcm: str,
    titulo: str,
    mensaje: str,
    data: Optional[dict] = None
) -> bool:
    """
    Envía una notificación push a un dispositivo específico
    
    Args:
        token_fcm: Token FCM del dispositivo destino
        titulo: Título de la notificación
        mensaje: Cuerpo de la notificación
        data: Datos adicionales (opcional)
    
    Returns:
        True si se envió correctamente, False si falló
    """
    if not _firebase_initialized:
        logger.warning("Firebase no está inicializado. No se puede enviar notificación push.")
        return False
    
    if not token_fcm:
        logger.warning("Token FCM vacío. No se puede enviar notificación push.")
        return False
    
    try:
        # Crear el mensaje
        builder = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=mensaje,
            ),
            token=token_fcm,
        )
        
        # Agregar datos personalizados si se proporcionan
        if data:
            builder = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=mensaje,
                ),
                data=data,
                token=token_fcm,
            )
        
        # Enviar el mensaje
        response = messaging.send(builder)
        logger.info(f"Notificación push enviada exitosamente: {response}")
        return True
        
    except firebase_admin._helpers.MessagingError as e:
        logger.error(f"Error de Firebase Messaging: {e}")
        return False
    except Exception as e:
        logger.error(f"Error al enviar notificación push: {e}")
        return False


def send_push_to_multiple_tokens(
    tokens: list,
    titulo: str,
    mensaje: str,
    data: Optional[dict] = None
) -> dict:
    """
    Envía una notificación push a múltiples dispositivos
    
    Args:
        tokens: Lista de tokens FCM
        titulo: Título de la notificación
        mensaje: Cuerpo de la notificación
        data: Datos adicionales (opcional)
    
    Returns:
        Dict con resultados de envío
    """
    if not _firebase_initialized:
        logger.warning("Firebase no está inicializado")
        return {"success": False, "error": "Firebase no inicializado"}
    
    if not tokens:
        return {"success": False, "error": "No hay tokens para enviar"}
    
    results = {
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=mensaje,
                ),
                data=data or {},
                token=token,
            )
            messaging.send(message)
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"token": token[:20] + "...", "error": str(e)})
    
    return results