from typing import Optional
import random
import string
from datetime import datetime


class PagoSimulado:
    TARJETAS_VALIDAS = {
        "4000056655665556": "visa",
        "5555555555554444": "mastercard",
        "378282246310005": "amex",
    }
    
    @staticmethod
    def generar_id_transaccion() -> str:
        """Genera un ID de transacción único"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"TXN-{timestamp}-{random_part}"
    
    @staticmethod
    def validar_tarjeta(numero_tarjeta: str) -> dict:
        """Valida el número de tarjeta"""
        numero_limpio = numero_tarjeta.replace(" ", "").replace("-", "")
        
        if not numero_limpio.isdigit():
            return {"valida": False, "error": "El número de tarjeta debe contener solo dígitos"}
        
        if len(numero_limpio) < 13 or len(numero_limpio) > 19:
            return {"valida": False, "error": "Número de tarjeta inválido"}
        
        if len(numero_limpio) < 4:
            return {"valida": False, "error": "Número de tarjeta muy corto"}
        
        ultimos_4 = numero_limpio[-4:]
        
        if numero_limpio[:4] in PagoSimulado.TARJETAS_VALIDAS:
            tipo = PagoSimulado.TARJETAS_VALIDAS[numero_limpio[:4]]
        elif numero_limpio[:2] in ["51", "52", "53", "54", "55"]:
            tipo = "mastercard"
        elif numero_limpio[0] == "4":
            tipo = "visa"
        else:
            tipo = "desconocido"
        
        return {
            "valida": True,
            "tipo": tipo,
            "ultimos_4": ultimos_4
        }
    
    @staticmethod
    def validar_cvv(cvv: str, tipo_tarjeta: str) -> bool:
        """Valida el CVV según el tipo de tarjeta"""
        if not cvv.isdigit():
            return False
        
        if tipo_tarjeta == "amex":
            return len(cvv) == 4
        return len(cvv) == 3
    
    @staticmethod
    def validar_expiracion(expira: str) -> dict:
        """Valida la fecha de expiración (MM/AA)"""
        try:
            partes = expira.split("/")
            if len(partes) != 2:
                return {"valida": False, "error": "Formato inválido. Use MM/AA"}
            
            mes, ano = partes
            mes = int(mes)
            ano = int("20" + ano)
            
            if mes < 1 or mes > 12:
                return {"valida": False, "error": "Mes inválido"}
            
            ahora = datetime.now()
            expira_date = datetime(ano, mes, 1)
            
            if expira_date < ahora:
                return {"valida": False, "error": "Tarjeta expirada"}
            
            return {"valida": True, "expira_mes": mes, "expira_ano": ano}
        except:
            return {"valida": False, "error": "Formato de fecha inválido"}
    
    @staticmethod
    def procesar_pago(
        numero_tarjeta: str,
        cvv: str,
        expira: str,
        monto: float,
        email: str,
        nombre_titular: str
    ) -> dict:
        """Procesa un pago simulado"""
        
        resultado_validacion = PagoSimulado.validar_tarjeta(numero_tarjeta)
        if not resultado_validacion["valida"]:
            return {
                "exitoso": False,
                "error": resultado_validacion["error"],
                "codigo": "TARJETA_INVALIDA"
            }
        
        tipo_tarjeta = resultado_validacion["tipo"]
        
        if not PagoSimulado.validar_cvv(cvv, tipo_tarjeta):
            return {
                "exitoso": False,
                "error": "CVV inválido",
                "codigo": "CVV_INVALIDO"
            }
        
        validacion_expira = PagoSimulado.validar_expiracion(expira)
        if not validacion_expira["valida"]:
            return {
                "exitoso": False,
                "error": validacion_expira["error"],
                "codigo": "TARJETA_EXPIRADA"
            }
        
        if monto <= 0:
            return {
                "exitoso": False,
                "error": "El monto debe ser mayor a 0",
                "codigo": "MONTO_INVALIDO"
            }
        
        if random.random() < 0.1:
            return {
                "exitoso": False,
                "error": "Transacción rechazada por el banco",
                "codigo": "RECHAZADO"
            }
        
        id_transaccion = PagoSimulado.generar_id_transaccion()
        
        return {
            "exitoso": True,
            "id_transaccion": id_transaccion,
            "monto": monto,
            "moneda": "USD",
            "estado": "aprobado",
            "tarjeta_tipo": tipo_tarjeta,
            "tarjeta_ultimos_4": resultado_validacion["ultimos_4"],
            "nombre_titular": nombre_titular,
            "email": email,
            "fecha": datetime.now().isoformat(),
            "mensaje": "Pago aprobado exitosamente"
        }
    
    @staticmethod
    def reembolsar_pago(id_transaccion: str) -> dict:
        """Simula un reembolso"""
        return {
            "exitoso": True,
            "id_reembolso": f"REF-{id_transaccion}",
            "id_transaccion_original": id_transaccion,
            "estado": "reembolsado",
            "fecha": datetime.now().isoformat(),
            "mensaje": "Reembolso procesado exitosamente"
        }
    
    @staticmethod
    def obtener_estado_transaccion(id_transaccion: str) -> dict:
        """Consulta el estado de una transacción"""
        return {
            "id_transaccion": id_transaccion,
            "estado": "completado",
            "fecha": datetime.now().isoformat()
        }


pasarela_pago = PagoSimulado()