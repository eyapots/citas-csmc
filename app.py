#!/usr/bin/env python3
"""
SISTEMA DE CITAS MÉDICAS v2.0
Aplicación web Flask con SQLite para gestión de citas.
Acceso multiusuario por internet con login.
"""

import os
import re
import io
import calendar
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import xlsxwriter

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DB_PATH = os.path.join(os.path.dirname(__file__), 'citas.db')

PROF_PALETTE = {
    "HUAPAYA ESPINOZA GIRALDO WILFREDO":    {'bg': '#203764', 'font': 'white'},
    "SALAS MORALES GONZALO AUGUSTO":        {'bg': '#385724', 'font': 'white'},
    "EQUIÑO CHAVEZ IRENE EXMENA":           {'bg': '#FBD5B5', 'font': 'black'},
    "SEQQUERA HUAMANI YENY VIKI":           {'bg': '#CCC0DA', 'font': 'black'},
    "RODRIGUEZ CONTRERAS ROSSANA CRISTINA": {'bg': '#B7DEE8', 'font': 'black'},
    "CHOQUE AVILES ANA LUZ":                {'bg': '#D8E4BC', 'font': 'black'},
    "HUAMANI AÑAMURO MERYLIN NATALY":       {'bg': '#FFD966', 'font': 'black'},
    "GALLEGOS PORTUGAL FELIX ABEL":         {'bg': '#BFBFBF', 'font': 'black'},
    "SUCA TINTA YUDITH DIANA":             {'bg': '#95B3D7', 'font': 'black'},
    "GARCIA PERALTA NARVY ZORAIDA":         {'bg': '#E6B8B7', 'font': 'black'},
    "COLQUEHUANCA PUMA LUZ MARY":           {'bg': '#7030A0', 'font': 'white'},
}

SPECIALTY_MAP = {
    "PSIQUIATRÍA": ["HUAPAYA ESPINOZA GIRALDO WILFREDO"],
    "MEDICINA":    ["SALAS MORALES GONZALO AUGUSTO"],
}

DIAS_ES = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']
DIAS_CORTO = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']

# ==============================================================================
# BASE DE DATOS
# ==============================================================================
def get_db():
    """Obtener conexión a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Mejor concurrencia
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Crear todas las tablas necesarias."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'operador',
            activo INTEGER DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS profesionales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            especialidad TEXT NOT NULL DEFAULT 'PSICOLOGÍA',
            color_bg TEXT DEFAULT '#CCCCCC',
            color_font TEXT DEFAULT 'black',
            orden INTEGER DEFAULT 99,
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS roles_mensuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profesional_id INTEGER NOT NULL,
            anio INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            dia INTEGER NOT NULL,
            turno TEXT NOT NULL,
            FOREIGN KEY (profesional_id) REFERENCES profesionales(id),
            UNIQUE(profesional_id, anio, mes, dia)
        );

        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profesional_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            turno TEXT NOT NULL,
            area TEXT NOT NULL,
            paciente TEXT DEFAULT '',
            dni TEXT DEFAULT '',
            celular TEXT DEFAULT '',
            observaciones TEXT DEFAULT '',
            estado TEXT DEFAULT 'Disponible',
            tipo_paciente TEXT DEFAULT '',
            asistencia TEXT DEFAULT 'Pendiente',
            creado_por INTEGER,
            modificado_por INTEGER,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modificado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profesional_id) REFERENCES profesionales(id),
            FOREIGN KEY (creado_por) REFERENCES usuarios(id),
            FOREIGN KEY (modificado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cita_id INTEGER,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            detalle TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cita_id) REFERENCES citas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha);
        CREATE INDEX IF NOT EXISTS idx_citas_prof ON citas(profesional_id);
        CREATE INDEX IF NOT EXISTS idx_citas_estado ON citas(estado);
        CREATE INDEX IF NOT EXISTS idx_roles_periodo ON roles_mensuales(anio, mes);
    ''')

    # Crear admin por defecto si no existe
    admin = conn.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?,?,?,?)",
            ('admin', generate_password_hash('admin123'), 'Administrador', 'admin')
        )

    # Insertar profesionales iniciales si la tabla está vacía
    count = conn.execute("SELECT COUNT(*) FROM profesionales").fetchone()[0]
    if count == 0:
        for i, (nombre, colores) in enumerate(PROF_PALETTE.items()):
            esp = 'PSICOLOGÍA'
            for area, profs in SPECIALTY_MAP.items():
                if nombre in profs:
                    esp = area
                    break
            conn.execute(
                "INSERT INTO profesionales (nombre, especialidad, color_bg, color_font, orden) VALUES (?,?,?,?,?)",
                (nombre, esp, colores['bg'], colores['font'], i)
            )

    conn.commit()
    conn.close()

# ==============================================================================
# AUTENTICACIÓN
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesión', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_rol') != 'admin':
            flash('Acceso denegado. Se requiere rol de administrador.', 'danger')
            return redirect(url_for('agenda'))
        return f(*args, **kwargs)
    return decorated

# ==============================================================================
# MOTOR DE GENERACIÓN DE CUPOS
# ==============================================================================
def parse_roster_text(text):
    """Parsear texto de rol mensual."""
    result = {}
    for line in text.strip().split('\n'):
        if ':' not in line:
            continue
        parts = line.split(':', 1)
        name = parts[0].strip().upper()
        sched_text = parts[1].strip()
        matches = re.findall(r'[Dd]ía\s+(\d+)\s+([A-Za-z]+)', sched_text)
        schedule = {}
        for day, code in matches:
            schedule[int(day)] = code.upper()
        if schedule:
            result[name] = schedule
    return result

def generate_slots(conn, year, month, roster_text=None):
    """Generar cupos para un mes. Preserva citas existentes si hay cambio de turno."""

    # Obtener profesionales activos
    profs = {r['nombre']: dict(r) for r in conn.execute(
        "SELECT * FROM profesionales WHERE activo=1"
    ).fetchall()}

    if roster_text:
        parsed = parse_roster_text(roster_text)
    else:
        # Construir desde la tabla roles_mensuales
        parsed = {}
        rows = conn.execute(
            "SELECT r.dia, r.turno, p.nombre FROM roles_mensuales r "
            "JOIN profesionales p ON p.id = r.profesional_id "
            "WHERE r.anio=? AND r.mes=?", (year, month)
        ).fetchall()
        for r in rows:
            parsed.setdefault(r['nombre'], {})[r['dia']] = r['turno']

    if not parsed:
        return 0

    num_days = calendar.monthrange(year, month)[1]

    # Obtener citas existentes con paciente (para migración de turnos)
    existing = {}
    rows = conn.execute(
        "SELECT c.*, p.nombre as prof_nombre FROM citas c "
        "JOIN profesionales p ON p.id = c.profesional_id "
        "WHERE c.fecha BETWEEN ? AND ? AND c.estado != 'Disponible'",
        (f"{year}-{month:02d}-01", f"{year}-{month:02d}-{num_days:02d}")
    ).fetchall()
    for r in rows:
        key = (r['prof_nombre'], r['fecha'])
        existing.setdefault(key, []).append(dict(r))

    # Eliminar cupos del mes
    conn.execute(
        "DELETE FROM citas WHERE fecha BETWEEN ? AND ?",
        (f"{year}-{month:02d}-01", f"{year}-{month:02d}-{num_days:02d}")
    )

    # Eliminar roles previos del mes
    conn.execute("DELETE FROM roles_mensuales WHERE anio=? AND mes=?", (year, month))

    count = 0
    for day in range(1, num_days + 1):
        try:
            curr_date = datetime(year, month, day)
        except ValueError:
            continue

        for prof_name, schedule in parsed.items():
            if day not in schedule:
                continue

            # Buscar profesional en BD (coincidencia flexible)
            prof_data = None
            for db_name, db_data in profs.items():
                n1 = prof_name.replace(" ", "").upper()
                n2 = db_name.replace(" ", "").upper()
                if n1 in n2 or n2 in n1:
                    prof_data = db_data
                    break

            if not prof_data:
                continue

            shift = schedule[day]
            is_med = prof_data['especialidad'] in ('MEDICINA', 'PSIQUIATRÍA')
            date_str = curr_date.strftime('%Y-%m-%d')

            # Guardar rol
            conn.execute(
                "INSERT OR REPLACE INTO roles_mensuales (profesional_id, anio, mes, dia, turno) VALUES (?,?,?,?,?)",
                (prof_data['id'], year, month, day, shift)
            )

            slots_to_create = []

            if shift in ('M', 'MT', 'GD'):
                start = "07:30"
                n_slots = 8 if is_med else 7
                duration = 40 if is_med else 45
                slots_to_create.extend(_make_slots(start, n_slots, duration, 'MAÑANA'))

            if shift in ('T', 'MT', 'GD'):
                start = "14:00" if is_med else "13:50"
                n_slots = 7 if is_med else 6
                duration = 40 if is_med else 45
                slots_to_create.extend(_make_slots(start, n_slots, duration, 'TARDE'))

            # Citas existentes para migración
            prev_appointments = existing.get((prof_data['nombre'], date_str), [])
            prev_by_order = sorted(prev_appointments, key=lambda x: x['hora_inicio'])

            for i, slot in enumerate(slots_to_create):
                pac = dni = cel = obs = estado = tipo = asist = ''
                pac = ''
                estado = 'Disponible'
                tipo = ''
                asist = 'Pendiente'
                creado = modificado = None

                # Migrar cita existente al nuevo cupo si existe
                if i < len(prev_by_order):
                    prev = prev_by_order[i]
                    pac = prev['paciente']
                    dni = prev['dni']
                    cel = prev['celular']
                    obs = prev['observaciones']
                    estado = prev['estado']
                    tipo = prev['tipo_paciente']
                    asist = prev['asistencia']
                    creado = prev['creado_por']
                    modificado = prev['modificado_por']

                conn.execute(
                    """INSERT INTO citas (profesional_id, fecha, hora_inicio, hora_fin, turno, area,
                       paciente, dni, celular, observaciones, estado, tipo_paciente, asistencia,
                       creado_por, modificado_por)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (prof_data['id'], date_str, slot['inicio'], slot['fin'], slot['turno'],
                     prof_data['especialidad'], pac, dni, cel, obs, estado, tipo, asist,
                     creado, modificado)
                )
                count += 1

    conn.commit()
    return count

def _make_slots(start_str, n, duration, turno):
    """Generar lista de horarios."""
    slots = []
    curr = datetime.strptime(start_str, "%H:%M")
    for _ in range(n):
        end = curr + timedelta(minutes=duration)
        slots.append({
            'inicio': curr.strftime('%H:%M'),
            'fin': end.strftime('%H:%M'),
            'turno': turno
        })
        curr = end
    return slots

# ==============================================================================
# RUTAS - AUTENTICACIÓN
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username=? AND activo=1", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_nombre'] = user['nombre']
            session['user_rol'] = user['rol']
            flash(f'Bienvenido, {user["nombre"]}', 'success')
            return redirect(url_for('agenda'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==============================================================================
# RUTAS - AGENDA PRINCIPAL
# ==============================================================================
@app.route('/')
@login_required
def agenda():
    conn = get_db()
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    prof_id = request.args.get('prof_id', '')
    fecha = request.args.get('fecha', '')

    profesionales = conn.execute(
        "SELECT * FROM profesionales WHERE activo=1 ORDER BY orden"
    ).fetchall()

    # Fechas disponibles
    fechas = []
    if prof_id:
        rows = conn.execute(
            "SELECT DISTINCT fecha FROM citas WHERE profesional_id=? ORDER BY fecha",
            (prof_id,)
        ).fetchall()
        fechas = [r['fecha'] for r in rows]

    # Citas
    citas = []
    if prof_id and fecha:
        citas = conn.execute(
            """SELECT c.*, p.nombre as prof_nombre, p.color_bg, p.color_font, p.especialidad
               FROM citas c JOIN profesionales p ON p.id = c.profesional_id
               WHERE c.profesional_id=? AND c.fecha=?
               ORDER BY c.turno, c.hora_inicio""",
            (prof_id, fecha)
        ).fetchall()

    # Info de fecha para el header
    fecha_info = ''
    if fecha:
        try:
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            dia_sem = DIAS_ES[dt.weekday()]
            fecha_info = f"{dt.day} {dia_sem} - {dt.strftime('%d/%m/%Y')}"
        except:
            fecha_info = fecha

    conn.close()
    return render_template('agenda.html',
        profesionales=profesionales, fechas=fechas, citas=citas,
        sel_prof=prof_id, sel_fecha=fecha, fecha_info=fecha_info,
        year=year, month=month, palette=PROF_PALETTE
    )

@app.route('/api/fechas/<int:prof_id>')
@login_required
def api_fechas(prof_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT fecha FROM citas WHERE profesional_id=? ORDER BY fecha",
        (prof_id,)
    ).fetchall()
    fechas = []
    for r in rows:
        try:
            dt = datetime.strptime(r['fecha'], '%Y-%m-%d')
            dia_sem = DIAS_CORTO[dt.weekday()]
            fechas.append({'value': r['fecha'], 'label': f"{dt.day} {dia_sem} ({dt.strftime('%d/%m')})"})
        except:
            fechas.append({'value': r['fecha'], 'label': r['fecha']})
    conn.close()
    return jsonify(fechas)

@app.route('/api/citas/<int:prof_id>/<fecha>')
@login_required
def api_citas(prof_id, fecha):
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, p.nombre as prof_nombre, p.color_bg, p.color_font
           FROM citas c JOIN profesionales p ON p.id = c.profesional_id
           WHERE c.profesional_id=? AND c.fecha=?
           ORDER BY c.turno, c.hora_inicio""",
        (prof_id, fecha)
    ).fetchall()
    citas = [dict(r) for r in rows]
    conn.close()
    return jsonify(citas)

# ==============================================================================
# RUTAS - GESTIÓN DE CITAS
# ==============================================================================
@app.route('/cita/agendar', methods=['POST'])
@login_required
def agendar_cita():
    cita_id = request.form.get('cita_id')
    paciente = request.form.get('paciente', '').strip().upper()
    dni = request.form.get('dni', '').strip()
    celular = request.form.get('celular', '').strip()
    obs = request.form.get('observaciones', '').strip()
    tipo = request.form.get('tipo_paciente', 'NUEVO')

    if not paciente:
        flash('El nombre del paciente es obligatorio', 'danger')
        return redirect(request.referrer or url_for('agenda'))

    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if not cita:
        flash('Cita no encontrada', 'danger')
        conn.close()
        return redirect(url_for('agenda'))

    if cita['estado'] != 'Disponible':
        flash('Este cupo ya está ocupado', 'warning')
        conn.close()
        return redirect(request.referrer or url_for('agenda'))

    conn.execute(
        """UPDATE citas SET paciente=?, dni=?, celular=?, observaciones=?, estado='Confirmado',
           tipo_paciente=?, creado_por=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP
           WHERE id=?""",
        (paciente, dni, celular, obs, tipo, session['user_id'], session['user_id'], cita_id)
    )

    # Historial
    conn.execute(
        "INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], 'AGENDAR', f'Paciente: {paciente} | DNI: {dni}')
    )
    conn.commit()
    conn.close()
    flash(f'Cita agendada: {paciente}', 'success')
    return redirect(request.referrer or url_for('agenda'))

@app.route('/cita/eliminar/<int:cita_id>', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if cita and cita['estado'] != 'Disponible':
        detalle = f"Eliminado: {cita['paciente']} | DNI: {cita['dni']}"
        conn.execute(
            """UPDATE citas SET paciente='', dni='', celular='', observaciones='',
               estado='Disponible', tipo_paciente='', asistencia='Pendiente',
               modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?""",
            (session['user_id'], cita_id)
        )
        conn.execute(
            "INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
            (cita_id, session['user_id'], 'ELIMINAR', detalle)
        )
        conn.commit()
        flash('Cita eliminada', 'info')
    conn.close()
    return redirect(request.referrer or url_for('agenda'))

@app.route('/cita/asistencia/<int:cita_id>/<estado>', methods=['POST'])
@login_required
def marcar_asistencia(cita_id, estado):
    if estado not in ('Asistió', 'No asistió', 'Pendiente'):
        abort(400)
    conn = get_db()
    conn.execute(
        "UPDATE citas SET asistencia=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?",
        (estado, session['user_id'], cita_id)
    )
    conn.execute(
        "INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], 'ASISTENCIA', f'Marcado como: {estado}')
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ==============================================================================
# RUTAS - GENERACIÓN MENSUAL
# ==============================================================================
@app.route('/generar', methods=['GET', 'POST'])
@admin_required
def generar():
    conn = get_db()
    if request.method == 'POST':
        year = int(request.form.get('year', datetime.now().year))
        month = int(request.form.get('month', datetime.now().month))
        roster_text = request.form.get('roster_text', '')

        if not roster_text.strip():
            flash('El texto del rol no puede estar vacío', 'danger')
            return redirect(url_for('generar'))

        count = generate_slots(conn, year, month, roster_text)
        conn.close()
        flash(f'✅ Generados {count} cupos para {calendar.month_name[month]} {year}', 'success')
        return redirect(url_for('agenda', year=year, month=month))

    conn.close()
    return render_template('generar.html',
        year=datetime.now().year, month=datetime.now().month,
        default_roster=get_default_roster()
    )

def get_default_roster():
    return """HUAPAYA ESPINOZA GIRALDO WILFREDO: Día 9 MT, día 10 MT, día 11 MT, día 12 MT, día 23 MT, día 24 MT, día 25 MT, día 26 MT.
SALAS MORALES GONZALO AUGUSTO: Día 2 T, día 3 T, día 4 MT, día 5 M, día 6 MT, día 7 M, día 12 T, día 13 MT, día 14 M, día 16 T, día 17 M, día 18 MT, día 19 T, día 20 M, día 23 T, día 24 T, día 25 M, día 26 MT, día 27 M, día 28 M.
EQUIÑO CHAVEZ IRENE EXMENA: Día 16 GD, día 17 M, día 18 T, día 19 T, día 20 GD, día 25 GD, día 26 T, día 27 M, día 28 GD.
SEQQUERA HUAMANI YENY VIKI: Día 2 MT, día 3 M, día 4 M, día 5 MT, día 6 M, día 9 M, día 10 T, día 11 M, día 12 T, día 13 MT, día 16 M, día 18 M, día 19 MT, día 20 M, día 21 MT, día 23 M, día 24 M, día 25 T, día 26 M, día 27 M.
RODRIGUEZ CONTRERAS ROSSANA CRISTINA: Día 4 MT, día 5 T, día 6 T, día 7 M, día 9 T, día 10 MT, día 11 T, día 12 M, día 13 T, día 14 MT, día 18 T, día 19 M, día 20 MT, día 21 M, día 23 MT, día 24 T, día 25 T, día 26 M, día 27 M, día 28 M.
CHOQUE AVILES ANA LUZ: Día 3 T, día 4 M, día 5 T, día 6 M, día 7 GD, día 9 M, día 10 T, día 11 M, día 12 T, día 13 GD, día 16 GD, día 17 T, día 18 GD, día 19 T, día 20 M, día 23 M, día 24 T, día 25 GD, día 26 T, día 27 M.
HUAMANI AÑAMURO MERYLIN NATALY: Día 2 MT, día 3 M, día 4 T, día 5 M, día 6 MT, día 9 T, día 10 M, día 11 T, día 12 M, día 13 M, día 17 M, día 18 M, día 19 M, día 20 T, día 21 MT, día 23 T, día 24 MT, día 25 M, día 26 MT, día 27 M.
GALLEGOS PORTUGAL FELIX ABEL: Día 2 GD, día 3 M, día 4 M, día 5 M, día 6 M, día 7 GD, día 9 M, día 10 M, día 11 T, día 12 M, día 13 GD, día 16 M, día 17 M, día 18 M, día 19 GD, día 23 M, día 24 M, día 25 M, día 26 GD, día 27 M.
SUCA TINTA YUDITH DIANA: Día 3 T, día 4 MT, día 5 T, día 6 M, día 9 M, día 10 T, día 11 M, día 12 T, día 13 MT, día 14 MT, día 16 T, día 17 T, día 18 M, día 19 T, día 20 M, día 23 MT, día 25 T, día 26 MT, día 27 M, día 28 T.
GARCIA PERALTA NARVY ZORAIDA: Día 2 T, día 3 MT, día 4 T, día 5 M, día 9 MT, día 10 M, día 11 MT, día 12 M, día 16 M, día 17 M, día 18 T, día 19 M, día 20 T, día 21 MT, día 23 T, día 24 T, día 25 M, día 26 T, día 27 MT, día 28 M.
COLQUEHUANCA PUMA LUZ MARY: Día 2 MT, día 3 MT, día 4 MT, día 5 MT, día 6 MT, día 9 MT, día 10 MT, día 11 MT, día 12 MT, día 13 MT, día 16 MT, día 17 MT, día 18 MT, día 19 MT, día 20 MT, día 23 MT, día 24 MT, día 25 MT, día 26 MT, día 27 MT."""

# ==============================================================================
# RUTAS - PROFESIONALES
# ==============================================================================
@app.route('/profesionales')
@admin_required
def profesionales():
    conn = get_db()
    profs = conn.execute("SELECT * FROM profesionales ORDER BY orden").fetchall()
    conn.close()
    return render_template('profesionales.html', profesionales=profs)

@app.route('/profesional/nuevo', methods=['POST'])
@admin_required
def nuevo_profesional():
    nombre = request.form.get('nombre', '').strip().upper()
    esp = request.form.get('especialidad', 'PSICOLOGÍA')
    color_bg = request.form.get('color_bg', '#CCCCCC')
    color_font = request.form.get('color_font', 'black')

    if not nombre:
        flash('El nombre es obligatorio', 'danger')
        return redirect(url_for('profesionales'))

    conn = get_db()
    try:
        max_orden = conn.execute("SELECT MAX(orden) FROM profesionales").fetchone()[0] or 0
        conn.execute(
            "INSERT INTO profesionales (nombre, especialidad, color_bg, color_font, orden) VALUES (?,?,?,?,?)",
            (nombre, esp, color_bg, color_font, max_orden + 1)
        )
        conn.commit()
        flash(f'Profesional {nombre} agregado', 'success')
    except sqlite3.IntegrityError:
        flash('Ya existe un profesional con ese nombre', 'warning')
    conn.close()
    return redirect(url_for('profesionales'))

@app.route('/profesional/toggle/<int:prof_id>', methods=['POST'])
@admin_required
def toggle_profesional(prof_id):
    conn = get_db()
    prof = conn.execute("SELECT * FROM profesionales WHERE id=?", (prof_id,)).fetchone()
    if prof:
        new_status = 0 if prof['activo'] else 1
        conn.execute("UPDATE profesionales SET activo=? WHERE id=?", (new_status, prof_id))
        conn.commit()
        accion = "activado" if new_status else "desactivado"
        flash(f'Profesional {accion}', 'info')
    conn.close()
    return redirect(url_for('profesionales'))

@app.route('/profesional/editar/<int:prof_id>', methods=['POST'])
@admin_required
def editar_profesional(prof_id):
    nombre = request.form.get('nombre', '').strip().upper()
    esp = request.form.get('especialidad', 'PSICOLOGÍA')
    color_bg = request.form.get('color_bg', '#CCCCCC')
    color_font = request.form.get('color_font', 'black')

    conn = get_db()
    conn.execute(
        "UPDATE profesionales SET nombre=?, especialidad=?, color_bg=?, color_font=? WHERE id=?",
        (nombre, esp, color_bg, color_font, prof_id)
    )
    conn.commit()
    conn.close()
    flash('Profesional actualizado', 'success')
    return redirect(url_for('profesionales'))

# ==============================================================================
# RUTAS - USUARIOS
# ==============================================================================
@app.route('/usuarios')
@admin_required
def usuarios():
    conn = get_db()
    users = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=users)

@app.route('/usuario/nuevo', methods=['POST'])
@admin_required
def nuevo_usuario():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    nombre = request.form.get('nombre', '').strip()
    rol = request.form.get('rol', 'operador')

    if not username or not password:
        flash('Usuario y contraseña son obligatorios', 'danger')
        return redirect(url_for('usuarios'))

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?,?,?,?)",
            (username, generate_password_hash(password), nombre, rol)
        )
        conn.commit()
        flash(f'Usuario {username} creado', 'success')
    except sqlite3.IntegrityError:
        flash('Ya existe ese nombre de usuario', 'warning')
    conn.close()
    return redirect(url_for('usuarios'))

@app.route('/usuario/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_usuario(user_id):
    if user_id == session.get('user_id'):
        flash('No puede desactivar su propia cuenta', 'danger')
        return redirect(url_for('usuarios'))
    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user['activo'] else 1
        conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (new_status, user_id))
        conn.commit()
    conn.close()
    return redirect(url_for('usuarios'))

# ==============================================================================
# RUTAS - REPORTES
# ==============================================================================
@app.route('/reportes')
@login_required
def reportes():
    conn = get_db()
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    # Estadísticas generales
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN estado='Confirmado' THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN estado='Disponible' THEN 1 ELSE 0 END) as disponibles,
            SUM(CASE WHEN asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
            SUM(CASE WHEN asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron,
            SUM(CASE WHEN tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
            SUM(CASE WHEN tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores
        FROM citas
        WHERE strftime('%Y', fecha)=? AND strftime('%m', fecha)=?
    """, (str(year), f"{month:02d}")).fetchone()

    # Por profesional
    by_prof = conn.execute("""
        SELECT p.nombre, p.color_bg, p.color_font, p.especialidad,
            COUNT(*) as total,
            SUM(CASE WHEN c.estado='Confirmado' THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN c.asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
            SUM(CASE WHEN c.asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron,
            SUM(CASE WHEN c.tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
            SUM(CASE WHEN c.tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores
        FROM citas c JOIN profesionales p ON p.id = c.profesional_id
        WHERE strftime('%Y', c.fecha)=? AND strftime('%m', c.fecha)=?
        GROUP BY p.id ORDER BY p.orden
    """, (str(year), f"{month:02d}")).fetchall()

    # Historial reciente
    historial = conn.execute("""
        SELECT h.*, u.nombre as usuario_nombre,
               c.paciente, c.fecha, c.hora_inicio, p.nombre as prof_nombre
        FROM historial h
        LEFT JOIN usuarios u ON u.id = h.usuario_id
        LEFT JOIN citas c ON c.id = h.cita_id
        LEFT JOIN profesionales p ON p.id = c.profesional_id
        ORDER BY h.fecha_hora DESC LIMIT 50
    """).fetchall()

    conn.close()
    return render_template('reportes.html',
        stats=stats, by_prof=by_prof, historial=historial,
        year=year, month=month
    )

# ==============================================================================
# RUTAS - EXPORTAR EXCEL
# ==============================================================================
@app.route('/exportar')
@login_required
def exportar_excel():
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    conn = get_db()
    rows = conn.execute("""
        SELECT c.fecha, c.turno, c.area, p.nombre as profesional,
               c.hora_inicio, c.hora_fin, c.paciente, c.dni, c.celular,
               c.observaciones, c.estado, c.tipo_paciente, c.asistencia,
               p.color_bg, p.color_font
        FROM citas c JOIN profesionales p ON p.id = c.profesional_id
        WHERE strftime('%Y', c.fecha)=? AND strftime('%m', c.fecha)=?
        ORDER BY c.fecha, c.turno, p.orden, c.hora_inicio
    """, (str(year), f"{month:02d}")).fetchall()
    conn.close()

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('AGENDA')

    fmt_h = wb.add_format({'bold': True, 'bg_color': '#404040', 'font_color': 'white',
                           'border': 1, 'align': 'center', 'valign': 'vcenter'})
    fmt_date = wb.add_format({'bg_color': '#000000', 'font_color': 'white', 'bold': True,
                              'align': 'center', 'valign': 'vcenter', 'border': 1})

    headers = ['FECHA', 'TURNO', 'ÁREA', 'PROFESIONAL', 'HORA', 'PACIENTE',
               'DNI', 'CELULAR', 'OBSERVACIONES', 'ESTADO', 'TIPO', 'ASISTENCIA']
    for i, h in enumerate(headers):
        ws.write(0, i, h, fmt_h)

    ws.set_column(0, 0, 12)
    ws.set_column(1, 2, 12)
    ws.set_column(3, 3, 35)
    ws.set_column(4, 4, 15)
    ws.set_column(5, 5, 35)

    fmt_cache = {}
    for i, row in enumerate(rows):
        r = i + 1
        row = dict(row)
        key = (row['color_bg'], row['color_font'])
        if key not in fmt_cache:
            fmt_cache[key] = {
                'c': wb.add_format({'bg_color': key[0], 'font_color': key[1],
                                    'border': 1, 'align': 'center', 'valign': 'vcenter'}),
                'l': wb.add_format({'bg_color': key[0], 'font_color': key[1],
                                    'border': 1, 'align': 'left', 'valign': 'vcenter', 'indent': 1}),
            }

        try:
            dt = datetime.strptime(row['fecha'], '%Y-%m-%d')
            dia_sem = DIAS_CORTO[dt.weekday()]
            fecha_vis = f"{dt.day} {dia_sem}"
        except:
            fecha_vis = row['fecha']

        hora = f"{row['hora_inicio']} - {row['hora_fin']}"
        fc = fmt_cache[key]['c']
        fl = fmt_cache[key]['l']

        ws.write(r, 0, fecha_vis, fmt_date)
        ws.write(r, 1, row['turno'], fc)
        ws.write(r, 2, row['area'], fc)
        ws.write(r, 3, row['profesional'], fl)
        ws.write(r, 4, hora, fc)
        ws.write(r, 5, row['paciente'], fl)
        ws.write(r, 6, row['dni'], fc)
        ws.write(r, 7, row['celular'], fc)
        ws.write(r, 8, row['observaciones'], fl)
        ws.write(r, 9, row['estado'], fc)
        ws.write(r, 10, row['tipo_paciente'], fc)
        ws.write(r, 11, row['asistencia'], fc)

    wb.close()
    output.seek(0)

    filename = f"Agenda_{calendar.month_name[month]}_{year}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==============================================================================
# INICIALIZACIÓN
# ==============================================================================
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
