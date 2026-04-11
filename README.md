# Asistente Vehicular API

Sistema de emergencia vehicular con FastAPI para el parcial de Sistemas de Información 2.

## Descripción del Proyecto

Asistente inteligente para emergencia vehicular que conecta clientes con talleres y técnicos. Analiza evidencias (foto, audio, texto) mediante IA para crear incidentes con especialidad, prioridad y seleccionar el taller más cercano.

## Actores del Sistema

| Actor | Descripción |
|-------|-------------|
| **Cliente** | Usuario que reporta emergencias y tiene vehículos registrados |
| **Dueño de Taller** | Gestiona un taller con ubicación geográfica y especialidad |
| **Técnico** | Pertenece a un taller, puede recibir assignments de emergencia |

---

## Estructura del Proyecto

```
backend/
├── app/
│   ├── main.py                 # Aplicación FastAPI
│   ├── core/                   # Configuración global
│   │   ├── config.py           # Variables de entorno
│   │   └── security.py        # JWT y encriptación
│   ├── db/                     # Base de datos
│   │   └── database.py        # Conexión SQLite/PostgreSQL
│   └── modulos/                # Módulos de negocio
│       ├── usuarios/           # Módulo de identidad
│       │   ├── models/        # Usuario, Tecnico, Notificacion
│       │   ├── schemas/       # Validación de datos
│       │   ├── services/      # Lógica de negocio
│       │   └── routers/       # Endpoints
│       └── activos/            # Módulo de activos
│           ├── models/        # Taller, Vehiculo
│           ├── schemas/       # Validación de datos
│           ├── services/      # Lógica de negocio
│           └── routers/       # Endpoints
├── Dockerfile
├── docker-compose.yml         # Desarrollo (SQLite)
├── docker-compose.prod.yml    # Producción (PostgreSQL)
├── requirements.txt
└── .env
```

---

## Modelos de Datos

### Módulo Usuarios

| Tabla | Campos |
|-------|--------|
| **Usuario** | id, email, password, username, nombre, telefono, rol |
| **Tecnico** | id, usuario_id, taller_id, disponible |
| **Notificacion** | id, usuario_id, titulo, mensaje, fecha_envio, tipo, leido |

### Módulo Activos

| Tabla | Campos |
|-------|--------|
| **Taller** | id, dueño_id, nombre, ubicacion_lat, ubicacion_lng, especialidad, telefono, horario_atencion |
| **Vehiculo** | id, cliente_id, placa, modelo, marca, color |

---

## Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **cliente** | Registrar y gestionar sus vehículos |
| **dueno** | Registrar y gestionar su taller |
| **tecnico** | Actualizar disponibilidad, asociado a un taller |

---

## Endpoints

### Módulo Usuarios

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/usuarios/usuario/register` | Registrar nuevo usuario |
| POST | `/usuarios/usuario/login` | Iniciar sesión (retorna JWT) |
| GET | `/usuarios/usuario/me` | Obtener perfil del usuario actual |
| GET | `/usuarios/usuario/{id}` | Obtener usuario por ID |
| GET | `/usuarios/usuario/` | Listar todos los usuarios |
| PUT | `/usuarios/usuario/{id}` | Actualizar usuario |
| DELETE | `/usuarios/usuario/{id}` | Eliminar usuario |
| POST | `/usuarios/tecnico/registrar` | Registrar como técnico |
| GET | `/usuarios/tecnico/{id}` | Obtener técnico por ID |
| GET | `/usuarios/tecnico/disponibles` | Listar técnicos disponibles |
| PUT | `/usuarios/tecnico/{id}/disponibilidad` | Actualizar disponibilidad |
| POST | `/usuarios/notificacion/` | Crear notificación |
| GET | `/usuarios/notificacion/mis-notificaciones/` | Notificaciones del usuario |

### Módulo Activos

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/activos/taller/` | Crear taller (solo dueños) |
| GET | `/activos/taller/{id}` | Obtener taller por ID |
| GET | `/activos/taller/mi-taller/` | Obtener taller del usuario |
| GET | `/activos/taller/` | Listar todos los talleres |
| GET | `/activos/taller/especialidad/` | Talleres por especialidad |
| PUT | `/activos/taller/{id}` | Actualizar taller |
| DELETE | `/activos/taller/{id}` | Eliminar taller |
| POST | `/activos/vehiculo/` | Crear vehículo (solo clientes) |
| GET | `/activos/vehiculo/{id}` | Obtener vehículo por ID |
| GET | `/activos/vehiculo/mis-vehiculos/` | Vehículos del usuario |
| GET | `/activos/vehiculo/` | Listar todos los vehículos |
| PUT | `/activos/vehiculo/{id}` | Actualizar vehículo |
| DELETE | `/activos/vehiculo/{id}` | Eliminar vehículo |

### Rutas Públicas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Raíz de la API |
| GET | `/health` | Health check |
| GET | `/docs` | Documentación Swagger UI |

---

## Instalación y Uso

### Requisitos Previos

- Python 3.11+
- Docker/Podman (para contenedores)

### Desarrollo Local (sin Docker)

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env

# 4. Ejecutar servidor
uvicorn app.main:app --reload
```

### Con Docker/Podman

```bash
# Desarrollo (SQLite)
podman-compose up -d
# o con Docker
docker-compose up -d

# Producción (PostgreSQL)
podman-compose -f docker-compose.prod.yml up -d
```

### Verificar Instalación

```bash
# API corriendo
curl http://localhost:8000/

# Documentación Swagger
# Abrir en navegador: http://localhost:8000/docs
```

---

## Tecnologías

| Tecnología | Uso |
|------------|-----|
| **FastAPI** | Framework web |
| **SQLAlchemy** | ORM para base de datos |
| **Pydantic** | Validación de datos |
| **JWT (python-jose)** | Autenticación |
| **bcrypt** | Encriptación de contraseñas |
| **SQLite** | Base de datos para desarrollo |
| **PostgreSQL** | Base de datos para producción |
| **Docker/Podman** | Contenedores |

---

## Configuración de Variables de Entorno

```env
# Desarrollo
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=tu-clave-secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Producción
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

## Autenticación

La API usa JWT (JSON Web Tokens) para autenticación.

1. Registrar usuario: `POST /usuarios/usuario/register`
2. Iniciar sesión: `POST /usuarios/usuario/login`
3. Copiar el `access_token` de la respuesta
4. En Swagger UI, hacer clic en "Authorize" y pegar el token
5. Ahora puedes acceder a endpoints protegidos

---

## Casos de Uso - Ciclo 1

1. **Registrar Usuario (Cliente/Dueño)**
2. **Autenticar Usuario**
3. **Gestionar Perfil de Taller**
4. **Registrar Ubicación Geográfica del Taller**
5. **Administrar Vehículos del Cliente**
6. **Gestionar Personal Técnico**
7. **Actualizar Disponibilidad del Técnico**

---

## Módulos Futuros (Ciclos 2-3)

- **Incidentes**: Reporte de emergencias, despacho inteligente
- **IA Core**: Procesamiento de evidencias (imagen, audio, texto)
- **Finanzas**: Pagos, comisiones, reportes

---

## Autores

- Proyecto para Sistemas de Información 2

---

## Licencia

Para uso académico
