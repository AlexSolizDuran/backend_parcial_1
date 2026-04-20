from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from .incidente import Incidente


class HistoriaIncidente(Base):
    __tablename__ = "historia_incidentes"

    id = Column(Integer, primary_key=True, index=True)
    incidente_id = Column(Integer, ForeignKey("incidentes.id"), nullable=False)
    fecha_hora = Column(DateTime, default=datetime.utcnow)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)

    incidente = relationship("Incidente", back_populates="historia_incidentes")