from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.database import Base, engine, SessionLocal
from app.modulos.usuarios.router import router as usuarios_router
from app.modulos.activos.router import router as activos_router
from app.modulos.incidentes.router import router as incidentes_router
from app.modulos.ia_core.routers.analisis import router as ia_router
from app.modulos.asignacion.router import router as asignacion_router
from app.modulos.finanzas.router import router as finanzas_router
from app.modulos.activos.services.especialidad import inicializar_especialidades
from app.core.websocket.manager import websocket_endpoint
from app.jobs.automatic_assignment import verificar_asignaciones_expiradas

Base.metadata.create_all(bind=engine)

scheduler = AsyncIOScheduler()

def verificar_expiradas_job():
    db = SessionLocal()
    try:
        resultados = verificar_asignaciones_expiradas(db)
        if resultados:
            logging.info(f"Procesadas {len(resultados)} asignaciones expiradas")
    except Exception as e:
        logging.error(f"Error en job de verificación: {e}")
    finally:
        db.close()

def inicializar_datos():
    db = SessionLocal()
    try:
        inicializar_especialidades(db)
    finally:
        db.close()

def iniciar_scheduler():
    scheduler.add_job(
        verificar_expiradas_job,
        trigger=IntervalTrigger(seconds=30),
        id="verificar_expiradas",
        name="Verificar asignaciones expiradas",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Scheduler iniciado - verificando expiradas cada 30 segundos")

def detener_scheduler():
    if scheduler.running:
        scheduler.shutdown()

inicializar_datos()

app = FastAPI(
    title="Asistente Vehicular API",
    description="API para sistema de emergencia vehicular",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios_router)
app.include_router(activos_router)
app.include_router(incidentes_router)
app.include_router(ia_router)
app.include_router(asignacion_router)
app.include_router(finanzas_router)


@app.get("/")
def root():
    return {"message": "MENSAJE DE PRUEBA", "status": "running"}


@app.get("/health")
def health_check():
    from app.db.database import engine
    pool = engine.pool
    return {
        "status": "healthy",
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }


@app.post("/reset-pool")
def reset_db_pool():
    from app.db.database import reset_pool
    return reset_pool()


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    logger = logging.getLogger(__name__)
    
    await websocket.accept()
    
    taller_id = websocket.query_params.get("taller_id")
    cliente_id = websocket.query_params.get("cliente_id")
    
    if taller_id:
        try:
            taller_id = int(taller_id)
        except ValueError:
            taller_id = None
    
    if cliente_id:
        try:
            cliente_id = int(cliente_id)
        except ValueError:
            cliente_id = None
    
    logger.info(f"WebSocket connection accepted, taller_id: {taller_id}, cliente_id: {cliente_id}")
    await websocket_endpoint(websocket, taller_id=taller_id, cliente_id=cliente_id)


@app.on_event("startup")
async def startup_event():
    iniciar_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    detener_scheduler()
