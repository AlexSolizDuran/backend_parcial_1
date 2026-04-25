from sqlalchemy import Column, Integer, Double, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Pago(Base):
    __tablename__ = "pago"

    id = Column(Integer, primary_key=True, index=True)
    asignacion_id = Column(Integer, ForeignKey("asignacion.id"), nullable=True)
    monto_total = Column(Double)
    monto_comision = Column(Double)
    estado = Column(Boolean, default=False)

    asignacion = relationship("Asignacion", back_populates="pago", lazy="select")
    