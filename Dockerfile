FROM python:3.11-slim

WORKDIR /app

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- EL CAMBIO ESTÁ AQUÍ ---
# Copia todo el proyecto manteniendo la estructura de carpetas
COPY . . 

EXPOSE 8000

# El comando debe apuntar a app.main porque ahora la carpeta app sí existe dentro de /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]