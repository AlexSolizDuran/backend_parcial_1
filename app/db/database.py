from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=30,
        max_overflow=50,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=60,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en get_db: {e}")
        db.rollback()
        raise
    finally:
        try:
            if db:
                db.close()  # CIERRE INCONDICIONAL: ¡Devuelve la conexión al pool!
        except Exception as e:
            logger.error(f"Error closing db: {e}")


def reset_pool():
    """Función para resetear el pool de conexiones"""
    logger.warning("Resetting database pool...")
    engine.dispose()
    logger.warning("Database pool disposed")
    return {"message": "Pool de conexiones reseteado"}


def verificar_pool():
    """Verificar estado del pool"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }
