# 🏥 SISTEMA DE CITAS MÉDICAS v2.0

## Guía de Instalación y Despliegue

---

## ¿Qué es esto?

Una aplicación web para gestionar citas médicas que permite:
- **4+ terminales simultáneas** accediendo desde cualquier lugar con internet
- Login por usuario (admin y operadores)
- Agendar, eliminar y gestionar citas
- Marcar asistencia (Asistió / No asistió)
- Tipo de paciente: NUEVO o CONTINUADOR
- Generación mensual de calendarios con migración automática de citas
- Agregar/desactivar profesionales
- Reportes con estadísticas por profesional
- Exportar a Excel
- Historial completo de acciones

---

## OPCIÓN 1: Ejecutar en tu computadora (Local)

### Requisitos
- Python 3.9 o superior (descarga de https://python.org)

### Pasos

1. **Descomprime** la carpeta `citas-app` en tu escritorio

2. **Abre una terminal** (CMD en Windows) y navega a la carpeta:
   ```
   cd escritorio/citas-app
   ```

3. **Instala las dependencias:**
   ```
   pip install -r requirements.txt
   ```

4. **Ejecuta la aplicación:**
   ```
   python app.py
   ```

5. **Abre un navegador** y ve a: http://localhost:5000

6. **Credenciales iniciales:**
   - Usuario: `admin`
   - Contraseña: `admin123`

> ⚠️ En modo local, solo las computadoras en la misma red pueden acceder.
> Para acceso por internet, usa la Opción 2.

---

## OPCIÓN 2: Desplegar en Internet GRATIS (Render.com)

### Paso 1 — Crear cuenta en GitHub
1. Ve a https://github.com y crea una cuenta gratuita
2. Crea un nuevo repositorio llamado `citas-app`
3. Sube todos los archivos de la carpeta `citas-app`

### Paso 2 — Crear cuenta en Render.com
1. Ve a https://render.com
2. Regístrate con tu cuenta de GitHub

### Paso 3 — Crear el servicio web
1. En Render, haz clic en **"New +"** → **"Web Service"**
2. Conecta tu repositorio `citas-app`
3. Configura:
   - **Name:** `citas-medicas`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. En **Environment Variables**, agrega:
   - `SECRET_KEY` = (cualquier texto largo aleatorio, por ejemplo: `mi-clave-secreta-2026-xyz`)
5. Haz clic en **"Create Web Service"**

### Paso 4 — ¡Listo!
- Render te dará una URL como: `https://citas-medicas.onrender.com`
- Comparte esa URL con las 4 terminales
- Cada persona inicia sesión con su usuario

> **NOTA:** El plan gratuito de Render "duerme" tras 15 minutos de inactividad.
> La primera carga puede tardar 30 segundos. Para uso continuo,
> considera el plan Starter ($7/mes) que mantiene la app siempre activa.

---

## OPCIÓN 3: Railway.app (Alternativa gratuita)

1. Ve a https://railway.app
2. Haz clic en "Deploy from GitHub"
3. Conecta tu repo
4. Railway detecta automáticamente Python
5. Agrega variable: `SECRET_KEY=tu-clave-secreta`
6. Deploy automático

---

## Primeros pasos después de instalar

1. **Inicia sesión** como admin/admin123
2. **Cambia la contraseña del admin** (importante en producción)
3. **Crea usuarios** para cada terminal en 🔑 Usuarios
4. **Verifica los profesionales** en 👥 Profesionales (ya vienen cargados los 11)
5. **Genera el calendario** en ⚙️ Generar:
   - Selecciona año y mes
   - Pega el texto del rol mensual
   - Haz clic en "REGENERAR CALENDARIO"
6. **Ve a 📅 Agenda** y comienza a agendar citas

---

## Estructura de archivos

```
citas-app/
├── app.py                 ← Aplicación principal (toda la lógica)
├── requirements.txt       ← Dependencias de Python
├── citas.db              ← Base de datos (se crea automáticamente)
├── static/
│   ├── css/
│   │   └── style.css     ← Estilos visuales
│   └── js/
│       └── app.js        ← JavaScript
└── templates/
    ├── base.html         ← Plantilla base con navegación
    ├── login.html        ← Página de login
    ├── agenda.html       ← Agenda principal (agendar citas)
    ├── generar.html      ← Generador de calendario mensual
    ├── profesionales.html ← Gestión de profesionales
    ├── usuarios.html     ← Gestión de usuarios
    └── reportes.html     ← Reportes y estadísticas
```

---

## Formato del Rol Mensual

Cada línea debe tener el formato:
```
NOMBRE COMPLETO: Día X TURNO, día X TURNO, ...
```

**Turnos válidos:**
- `M` = Mañana (07:30 - según especialidad)
- `T` = Tarde (13:50 o 14:00 según especialidad)
- `MT` = Mañana + Tarde
- `GD` = Guardia Diurna (Mañana + Tarde)

**Cupos por turno:**
| Especialidad | Mañana | Tarde | Duración |
|---|---|---|---|
| Psicología | 7 cupos | 6 cupos | 45 min |
| Medicina/Psiquiatría | 8 cupos | 7 cupos | 40 min |

---

## Soporte

Si tienes problemas:
1. Verifica que Python esté instalado: `python --version`
2. Verifica que las dependencias estén instaladas: `pip list`
3. Revisa la terminal por mensajes de error
4. La base de datos se puede reiniciar eliminando `citas.db`
