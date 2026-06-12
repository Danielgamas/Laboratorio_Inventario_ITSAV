# Sistema Web de Inventario y Préstamos - Laboratorio ISC ITSAV

Versión con interfaz institucional tipo SIE, separación de perfiles y flujo de préstamo por roles.

## Tecnologías

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLite
- Bootstrap 5
- Git/GitHub

## Funciones principales

### Administrador

- Dashboard con métricas del laboratorio.
- CRUD completo de equipos.
- CRUD completo de usuarios.
- Registro directo de préstamos.
- Aprobación o rechazo de solicitudes hechas por estudiantes.
- Registro de devoluciones.
- Reportes básicos del inventario y préstamos.

### Estudiante

- Portal propio del estudiante.
- Consulta de equipos disponibles.
- Solicitud de préstamo.
- Seguimiento de solicitudes: Solicitado, Activo, Devuelto, Vencido o Rechazado.

### Consulta pública

- Vista de solo lectura para mostrar equipos disponibles.

## Credenciales demo

- Administrador: `admin` / `1234`
- Estudiante: `estudiante` / `1234`

## Instalación en Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abrir:

```text
http://127.0.0.1:5000
```

## Reiniciar base de datos

```bash
python init_db.py
```

La base se crea automáticamente en `instance/inventario.db` con datos de prueba.
