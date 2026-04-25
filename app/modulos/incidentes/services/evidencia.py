from sqlalchemy.orm import Session
from typing import List, Optional
from app.modulos.incidentes.models.evidencia import Evidencia
from app.modulos.incidentes.schemas.evidencia import EvidenciaCreate, EvidenciaUpdate


def crear_evidencia(db: Session, evidencia: EvidenciaCreate, transcripcion: Optional[str] = None, descripcion: Optional[str] = None) -> Evidencia:
    db_evidencia = Evidencia(
        incidente_id=evidencia.incidente_id,
        tipo=evidencia.tipo,
        url_archivo=evidencia.url_archivo,
        contenido=evidencia.contenido,
        transcripcion=transcripcion,
        descripcion=descripcion
    )
    db.add(db_evidencia)
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def obtener_evidencia(db: Session, evidencia_id: int) -> Optional[Evidencia]:
    return db.query(Evidencia).filter(Evidencia.id == evidencia_id).first()


def obtener_evidencias_incidente(db: Session, incidente_id: int) -> List[Evidencia]:
    return db.query(Evidencia).filter(Evidencia.incidente_id == incidente_id).all()


def actualizar_evidencia(db: Session, evidencia_id: int, evidencia_update: EvidenciaUpdate) -> Optional[Evidencia]:
    db_evidencia = obtener_evidencia(db, evidencia_id)
    if not db_evidencia:
        return None
    
    update_data = evidencia_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_evidencia, field, value)
    
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def eliminar_evidencia(db: Session, evidencia_id: int) -> bool:
    db_evidencia = obtener_evidencia(db, evidencia_id)
    if not db_evidencia:
        return False
    
    db.delete(db_evidencia)
    db.commit()
    return True