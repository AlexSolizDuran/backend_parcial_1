from sqlalchemy import Integer, Column, Double, DateTime, ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
import enum
from app.db.database import Base

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)


class EstadoAsignacion(str, enum.Enum):
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"
    expirada = "expirada"
    completada = "completada"


class Asignacion(Base):
    __tablename__ = "asignacion"

    id = Column(Integer, primary_key=True, index=True)
    incidente_id = Column(Integer, ForeignKey("incidentes.id"), nullable=False)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=False)
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"), nullable=True)
    estado = Column(SQLEnum(EstadoAsignacion), default=EstadoAsignacion.pendiente)
    fecha_asignacion = Column(DateTime, default=now_bolivia)
    fecha_aceptacion = Column(DateTime, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    fecha_expiracion = Column(DateTime, nullable=True)
    intentos = Column(Integer, default=0)
    rechazados_ids = Column(String, default="")
    proximo_reintento = Column(DateTime, nullable=True)

    tecnico = relationship("Tecnico", foreign_keys=[tecnico_id])
    taller = relationship("Taller", foreign_keys=[taller_id])
    pago = relationship("Pago", back_populates="asignacion", lazy="select")