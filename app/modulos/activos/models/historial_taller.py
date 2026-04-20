from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class HistorialTaller(Base):
    __tablename__ = "historial_taller"

    id = Column(Integer, primary_key=True, index=True)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    tipo = Column(String, nullable=False)  # incidente_llegada, incidente_aceptado, incidente_rechazado, incidente_cancelado, tecnico_termino, etc.

    # Relaciones
    taller = relationship("Taller", back_populates="historial")