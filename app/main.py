from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.db.database import Base, engine
from app.modulos.usuarios.router import router as usuarios_router
from app.modulos.activos.router import router as activos_router
from app.modulos.incidentes.routers.incidente import router as incidentes_router
from app.modulos.incidentes.routers.historia_incidente import router as historia_incidente_router
from app.modulos.ia_core.routers.analisis import router as ia_router
from app.core.websocket.manager import websocket_endpoint

Base.metadata.create_all(bind=engine)

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
app.include_router(historia_incidente_router)
app.include_router(ia_router)


@app.get("/")
def root():
    return {"message": "MENSAJE DE PRUEBA", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_route(websocket, taller_id: int = None):
    """WebSocket endpoint for real-time notifications"""
    await websocket_endpoint(websocket, taller_id)
