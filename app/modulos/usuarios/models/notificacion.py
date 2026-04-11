from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String, nullable=False)
    mensaje = Column(String, nullable=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    tipo = Column(String, default="alerta")
    leido = Column(Boolean, default=False)

    usuario = relationship("Usuario", back_populates="notificaciones")
