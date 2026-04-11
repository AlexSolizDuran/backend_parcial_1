from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Taller(Base):
    __tablename__ = "talleres"

    id = Column(Integer, primary_key=True, index=True)
    dueño_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    ubicacion_lat = Column(Float, nullable=False)
    ubicacion_lng = Column(Float, nullable=False)
    especialidad = Column(String, nullable=False)
    telefono = Column(String)
    horario_atencion = Column(String)

    dueño = relationship("Usuario", backref="taller")
    tecnicos = relationship("Tecnico", back_populates="taller")
