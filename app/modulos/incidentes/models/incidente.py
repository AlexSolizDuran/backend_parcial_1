from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

BOLIVIA_TZ = timezone(timedelta(hours=-4))

def now_bolivia():
    return datetime.now(BOLIVIA_TZ)


class EstadoIncidente(str, enum.Enum):
    reportado = "reportado"
    asignado = "asignado"
    en_camino = "en_camino"
    en_sitio = "en_sitio"
    finalizado = "finalizado"
    cancelado = "cancelado"
    incluido = "incluido"
    sin_talleres = "sin_talleres"


class PrioridadIncidente(str, enum.Enum):
    baja = "baja"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class Incidente(Base):
    __tablename__ = "incidentes"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True)
    ubicacion_lat = Column(Float, nullable=False)
    ubicacion_lng = Column(Float, nullable=False)
    especialidad_ia = Column(String, nullable=True)
    descripcion_ia = Column(Text, nullable=True)
    prioridad = Column(SQLEnum(PrioridadIncidente), default=PrioridadIncidente.media)
    estado = Column(SQLEnum(EstadoIncidente), nullable=True, default=EstadoIncidente.reportado)
    descripcion_original = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    requiere_mas_evidencia = Column(Integer, default=0)
    mensaje_solicitud = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=now_bolivia)
    fecha_actualizacion = Column(DateTime, default=now_bolivia, onupdate=now_bolivia)

    cliente = relationship("Usuario", back_populates="incidentes")
    vehiculo = relationship("Vehiculo", back_populates="incidentes")
    evidencias = relationship("Evidencia", back_populates="incidente", cascade="all, delete-orphan")
    historia_incidentes = relationship("HistoriaIncidente", back_populates="incidente", cascade="all, delete-orphan")