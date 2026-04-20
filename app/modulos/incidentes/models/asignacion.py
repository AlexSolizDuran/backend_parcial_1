from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base
from .incidente import Incidente


class EstadoAsignacion(str, enum.Enum):
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"
    expirada = "expirada"


class Asignacion(Base):
    __tablename__ = "asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    incidente_id = Column(Integer, ForeignKey("incidentes.id"), nullable=False)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False)
    tecnico_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    estado = Column(SQLEnum(EstadoAsignacion), default=EstadoAsignacion.pendiente)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    fecha_aceptacion = Column(DateTime, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)

    # Relaciones
    incidente = relationship("Incidente", back_populates="asignaciones")
    taller = relationship("Taller", back_populates="asignaciones")
    tecnico = relationship("Usuario", foreign_keys=[tecnico_id])