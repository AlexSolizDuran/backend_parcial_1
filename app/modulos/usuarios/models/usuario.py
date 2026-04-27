from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base


class RolEnum(str, enum.Enum):
    cliente = "cliente"
    dueno = "dueno"
    tecnico = "tecnico"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    telefono = Column(String)
    rol = Column(SQLEnum(RolEnum), default=RolEnum.cliente)
    fcm_token = Column(String, nullable=True)

    vehiculos = relationship("Vehiculo", back_populates="cliente")
    notificaciones = relationship("Notificacion", back_populates="usuario")
    
    # AGREGA ESTA LÍNEA:
    incidentes = relationship("Incidente", back_populates="cliente")
