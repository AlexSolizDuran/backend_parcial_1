from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.modulos.usuarios.router import router as usuarios_router
from app.modulos.activos.router import router as activos_router

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


@app.get("/")
def root():
    return {"message": "MENSAJE DE PRUEBA", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
