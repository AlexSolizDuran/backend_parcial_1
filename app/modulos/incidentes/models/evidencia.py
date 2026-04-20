from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from .incidente import Incidente


class Evidencia(Base):
    __tablename__ = "evidencias"

    id = Column(Integer, primary_key=True, index=True)
    incidente_id = Column(Integer, ForeignKey("incidentes.id"), nullable=False)
    tipo = Column(String, nullable=False)  # foto, audio, texto
    url_archivo = Column(String, nullable=True)  # Ruta o URL del archivo almacenado (nullable para texto)
    contenido = Column(Text, nullable=True)  # Para texto: contenido directo
    transcripcion = Column(Text, nullable=True)  # Para audio: texto transcrito
    descripcion = Column(Text, nullable=True)  # Descripción corta generada por IA
    fecha_subida = Column(DateTime, default=datetime.utcnow)

    incidente = relationship("Incidente", back_populates="evidencias")