from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from app.db.database import Base
from .incidente import Incidente

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)


class Evidencia(Base):
    __tablename__ = "evidencias"

    id = Column(Integer, primary_key=True, index=True)
    incidente_id = Column(Integer, ForeignKey("incidentes.id"), nullable=False)
    tipo = Column(String, nullable=False)
    url_archivo = Column(String, nullable=True)
    contenido = Column(Text, nullable=True)
    transcripcion = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    fecha_subida = Column(DateTime, default=now_bolivia)

    incidente = relationship("Incidente", back_populates="evidencias")