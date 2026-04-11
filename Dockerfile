FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el CONTENIDO de tu carpeta app local a la raíz /app del contenedor
COPY app/ . 

EXPOSE 8000

# Como ahora main.py está en la raíz (/app/main.py), el comando cambia:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
