from sqlalchemy import Column, Integer, Double, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from app.db.database import Base

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)


class Pago(Base):
    __tablename__ = "pago"

    id = Column(Integer, primary_key=True, index=True)
    asignacion_id = Column(Integer, ForeignKey("asignacion.id"), nullable=True)
    monto_total = Column(Double)
    monto_comision = Column(Double)
    estado = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=now_bolivia)

    asignacion = relationship("Asignacion", back_populates="pago", lazy="select")
    