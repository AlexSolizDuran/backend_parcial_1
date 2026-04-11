from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Tecnico(Base):
    __tablename__ = "tecnicos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    taller_id = Column(Integer, ForeignKey("talleres.id"), nullable=True)
    disponible = Column(Boolean, default=True)

    usuario = relationship("Usuario", backref="tecnico")
    taller = relationship("Taller", back_populates="tecnicos")
