from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    placa = Column(String, unique=True, index=True, nullable=False)
    modelo = Column(String, nullable=False)
    marca = Column(String, nullable=False)
    color = Column(String)

    cliente = relationship("Usuario", back_populates="vehiculos")
