from sqlalchemy import Column, Integer, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


taller_especialidades = Table(
    'taller_especialidades',
    Base.metadata,
    Column('taller_id', Integer, ForeignKey('talleres.id'), primary_key=True),
    Column('especialidad_id', Integer, ForeignKey('especialidades.id'), primary_key=True)
)


class Especialidad(Base):
    __tablename__ = "especialidades"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)

    talleres = relationship("Taller", secondary=taller_especialidades, back_populates="especialidades")