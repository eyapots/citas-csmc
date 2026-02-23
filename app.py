#!/usr/bin/env python3
"""
SISTEMA DE CITAS MÉDICAS v2.0
Aplicación web Flask con SQLite para gestión de citas.
Templates embebidos para evitar problemas de despliegue.
"""

import os
import re
import io
import calendar
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, request, redirect, url_for,
    session, flash, jsonify, send_file, abort, make_response
)
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import xlsxwriter

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DB_PATH = os.path.join('/tmp', 'citas.db')

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
# CSS EMBEBIDO
# ==============================================================================
CSS = """
:root{--primary:#1a365d;--primary-light:#2b5797;--accent:#2e7d32;--accent-light:#4caf50;--danger:#c62828;--danger-light:#ef5350;--warning:#e65100;--info:#0277bd;--bg:#f0f2f5;--card-bg:#fff;--text:#1a1a2e;--text-muted:#6b7280;--border:#e2e8f0;--shadow:0 1px 3px rgba(0,0,0,.08);--radius:8px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;min-height:100vh}
.navbar{background:var(--primary);color:#fff;display:flex;align-items:center;padding:0 1.5rem;height:56px;box-shadow:0 2px 8px rgba(0,0,0,.15);position:sticky;top:0;z-index:100;gap:1rem;flex-wrap:wrap}
.nav-brand{display:flex;align-items:center;gap:.5rem;flex-shrink:0}
.nav-title{font-weight:700;font-size:.9rem;letter-spacing:.5px}
.nav-links{display:flex;gap:.25rem;flex:1;overflow-x:auto}
.nav-link{color:rgba(255,255,255,.75);text-decoration:none;padding:.4rem .75rem;border-radius:4px;font-size:.82rem;font-weight:500;white-space:nowrap;transition:all .15s}
.nav-link:hover,.nav-link.active{background:rgba(255,255,255,.2);color:#fff}
.nav-user{display:flex;align-items:center;gap:.5rem;flex-shrink:0}
.user-badge{background:rgba(255,255,255,.15);padding:.25rem .6rem;border-radius:20px;font-size:.78rem}
.btn-logout{color:rgba(255,255,255,.7);text-decoration:none;font-size:.78rem;padding:.25rem .5rem;border-radius:4px}
.btn-logout:hover{background:rgba(255,0,0,.3);color:#fff}
.container{max-width:1280px;margin:0 auto;padding:1.5rem}
.page-header{margin-bottom:1.5rem}
.page-header h2{font-size:1.4rem;font-weight:700;color:var(--primary)}
.card{background:var(--card-bg);border-radius:var(--radius);box-shadow:var(--shadow);padding:1.25rem;margin-bottom:1.25rem;border:1px solid var(--border)}
.card h3{font-size:1.05rem;font-weight:600;margin-bottom:1rem;color:var(--primary)}
.filter-row{display:flex;gap:1rem;align-items:flex-end;flex-wrap:wrap}
.filter-group{display:flex;flex-direction:column;gap:.3rem;flex:1;min-width:200px}
.filter-group label{font-size:.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px}
.form-group{margin-bottom:.8rem}
.form-group label{display:block;font-size:.82rem;font-weight:600;margin-bottom:.3rem}
.form-input,.form-select,.form-textarea{width:100%;padding:.5rem .75rem;border:1.5px solid var(--border);border-radius:4px;font-family:inherit;font-size:.88rem;background:#fff;transition:border-color .15s}
.form-input:focus,.form-select:focus,.form-textarea:focus{outline:none;border-color:var(--primary-light);box-shadow:0 0 0 3px rgba(43,87,151,.1)}
.form-textarea{font-family:monospace;font-size:.78rem;line-height:1.6;resize:vertical}
.form-row{display:flex;gap:.75rem}
.form-row .form-group{flex:1}
.form-help{display:block;font-size:.75rem;color:var(--text-muted);margin-top:.3rem}
.form-actions{margin-top:1rem;text-align:center}
.form-color{width:60px;height:36px;border:1px solid var(--border);border-radius:4px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:.3rem;padding:.5rem 1rem;border:none;border-radius:4px;font-family:inherit;font-size:.85rem;font-weight:600;cursor:pointer;transition:all .15s;text-decoration:none}
.btn:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
.btn-primary{background:var(--primary);color:#fff}.btn-primary:hover{background:var(--primary-light)}
.btn-success{background:var(--accent);color:#fff}.btn-success:hover{background:var(--accent-light)}
.btn-danger{background:var(--danger);color:#fff}.btn-danger:hover{background:var(--danger-light)}
.btn-warning{background:var(--warning);color:#fff}
.btn-secondary{background:#e2e8f0;color:var(--text)}.btn-secondary:hover{background:#cbd5e1}
.btn-sm{padding:.3rem .6rem;font-size:.78rem}
.btn-lg{padding:.75rem 2rem;font-size:1rem}
.btn-full{width:100%;justify-content:center}
.date-banner{background:var(--primary);color:#fff;padding:.75rem 1.25rem;border-radius:var(--radius);display:flex;align-items:center;gap:.75rem;margin-bottom:1rem;font-size:.9rem;flex-wrap:wrap}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:20px;font-size:.72rem;font-weight:600}
.badge-success{background:#c6f6d5;color:#22543d}.badge-danger{background:#fed7d7;color:#9b2c2c}
.badge-info{background:#bee3f8;color:#2a4365}.badge-warning{background:#fefcbf;color:#744210}
.badge-admin{background:#e9d8fd;color:#553c9a}.badge-new{background:#fef3c7;color:#92400e}
.badge-cont{background:#dbeafe;color:#1e40af}
.table-wrapper{overflow-x:auto;border-radius:var(--radius)}
table.citas-table{width:100%;border-collapse:collapse;font-size:.85rem}
.citas-table th{background:#f8fafc;padding:.6rem .75rem;text-align:left;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);border-bottom:2px solid var(--border);white-space:nowrap}
.citas-table td{padding:.5rem .75rem;border-bottom:1px solid var(--border);vertical-align:middle}
.cita-row{transition:background .1s}.cita-row:hover{background:#f8fafc}
.row-disponible{border-left:4px solid var(--accent-light)}
.row-inactive{opacity:.5}
.td-hora{font-family:monospace;font-size:.82rem;white-space:nowrap}
.paciente-nombre{font-weight:600}
.text-available{color:var(--accent);font-weight:500}
.text-muted{color:var(--text-muted)}.text-success{color:var(--accent)}.text-danger{color:var(--danger)}.text-center{text-align:center}
.turno-divider td{background:#f1f5f9;padding:.5rem .75rem;border:none}
.turno-label{font-weight:700;font-size:.82rem;letter-spacing:.5px}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:.3rem}
.status-confirmado{background:var(--danger)}.status-disponible{background:var(--accent)}
.asistencia-btns{display:flex;gap:.25rem}
.btn-asist{width:30px;height:30px;border:1.5px solid var(--border);border-radius:4px;background:#fff;cursor:pointer;font-size:.85rem;display:flex;align-items:center;justify-content:center;transition:all .15s}
.btn-asist:hover{transform:scale(1.1)}
.btn-asist-active{border-color:var(--accent);background:#f0fff4;box-shadow:0 0 0 2px rgba(46,125,50,.2)}
.btn-asist-no-active{border-color:var(--danger);background:#fff5f5;box-shadow:0 0 0 2px rgba(198,40,40,.2)}
.prof-chip{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.78rem;font-weight:600;white-space:nowrap}
.color-swatch{display:inline-flex;align-items:center;justify-content:center;width:40px;height:28px;border-radius:4px;font-weight:700;font-size:.8rem;border:1px solid rgba(0,0,0,.1)}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:.75rem;margin-bottom:1.25rem}
.stat-card{background:#fff;border-radius:var(--radius);padding:1rem;text-align:center;box-shadow:var(--shadow);border:1px solid var(--border);border-top:3px solid var(--border)}
.stat-total{border-top-color:var(--primary)}.stat-confirmed{border-top-color:var(--info)}
.stat-available{border-top-color:var(--accent)}.stat-attended{border-top-color:#2e7d32}
.stat-absent{border-top-color:var(--danger)}.stat-new{border-top-color:#e65100}
.stat-cont{border-top-color:#6a1b9a}.stat-rate{border-top-color:#00838f}
.stat-number{font-size:1.8rem;font-weight:700;color:var(--primary);line-height:1}
.stat-label{font-size:.72rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:.3px;margin-top:.3rem}
.progress-bar{width:100%;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;margin-bottom:.2rem}
.progress-fill{height:100%;background:var(--accent);border-radius:3px;transition:width .3s}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:200;padding:1rem}
.modal-content{background:#fff;border-radius:var(--radius);box-shadow:0 4px 12px rgba(0,0,0,.1);width:100%;max-width:480px;max-height:90vh;overflow-y:auto}
.modal-header{display:flex;justify-content:space-between;align-items:center;padding:1rem 1.25rem;border-bottom:1px solid var(--border)}
.modal-header h3{margin:0;font-size:1.05rem}
.modal-close{width:32px;height:32px;border:none;background:#f1f5f9;border-radius:50%;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center}
.modal-body{padding:1.25rem}
.modal-hora-display{background:#f0f9ff;padding:.5rem;border-radius:4px;text-align:center;font-weight:600;font-family:monospace;margin-bottom:1rem;color:var(--primary)}
.modal-footer{padding:.75rem 1.25rem;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:.5rem}
.flash-container{margin-bottom:1rem}
.flash{padding:.6rem 1rem;border-radius:4px;margin-bottom:.5rem;display:flex;justify-content:space-between;align-items:center;font-size:.88rem}
.flash-success{background:#f0fff4;color:#22543d;border:1px solid #c6f6d5}
.flash-danger{background:#fff5f5;color:#9b2c2c;border:1px solid #fed7d7}
.flash-warning{background:#fffbeb;color:#92400e;border:1px solid #fef3c7}
.flash-info{background:#eff6ff;color:#1e40af;border:1px solid #dbeafe}
.flash-close{background:none;border:none;font-size:1.2rem;cursor:pointer;opacity:.5;padding:0 .3rem}
.login-wrapper{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a365d 0%,#2b5797 50%,#1a365d 100%);padding:1rem}
.login-card{background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.3);padding:2.5rem;width:100%;max-width:400px}
.login-header{text-align:center;margin-bottom:1.5rem}
.login-icon{font-size:3rem;display:block;margin-bottom:.5rem}
.login-header h1{font-size:1.4rem;color:var(--primary);margin-bottom:.25rem}
.login-header p{color:var(--text-muted);font-size:.88rem}
.login-form .form-group{margin-bottom:1rem}
.login-form .btn{margin-top:.5rem;padding:.65rem;font-size:.95rem}
.login-footer{text-align:center;margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border);color:var(--text-muted)}
.empty-state{text-align:center;padding:3rem 1rem;color:var(--text-muted)}
.empty-icon{font-size:3rem;margin-bottom:.5rem}
.empty-state h3{color:var(--text);margin-bottom:.5rem}
@media(max-width:768px){.navbar{flex-wrap:wrap;height:auto;padding:.5rem 1rem;gap:.5rem}.nav-links{order:3;width:100%;padding-bottom:.5rem}.container{padding:1rem}.filter-row,.form-row{flex-direction:column}.filter-group{min-width:unset}.stats-grid{grid-template-columns:repeat(2,1fr)}.date-banner{flex-direction:column;align-items:flex-start}}
"""

# ==============================================================================
# HTML HELPERS
# ==============================================================================
def flash_html():
    msgs = session.pop('_flashes', []) if '_flashes' in session else []
    if not msgs:
        return ''
    html = '<div class="flash-container">'
    for cat, msg in msgs:
        html += f'<div class="flash flash-{cat}">{msg}<button class="flash-close" onclick="this.parentElement.remove()">×</button></div>'
    html += '</div>'
    return html

def get_flashes():
    """Get flash messages manually"""
    msgs = []
    flashes = session.pop('_flashes', [])
    for f in flashes:
        msgs.append(f)
    return msgs

def navbar_html():
    if 'user_id' not in session:
        return ''
    is_admin = session.get('user_rol') == 'admin'
    admin_links = ''
    if is_admin:
        admin_links = f'''
        <a href="/generar" class="nav-link">⚙️ Generar</a>
        <a href="/profesionales" class="nav-link">👥 Profesionales</a>
        <a href="/usuarios" class="nav-link">🔑 Usuarios</a>
        '''
    return f'''<nav class="navbar">
        <div class="nav-brand"><span style="font-size:1.4rem">🏥</span><span class="nav-title">SISTEMA DE CITAS</span></div>
        <div class="nav-links">
            <a href="/" class="nav-link">📅 Agenda</a>
            {admin_links}
            <a href="/reportes" class="nav-link">📊 Reportes</a>
            <a href="/exportar" class="nav-link">📥 Excel</a>
        </div>
        <div class="nav-user">
            <span class="user-badge">{session.get('user_nombre','')}</span>
            <a href="/logout" class="btn-logout">Salir</a>
        </div>
    </nav>'''

def page(title, content, flash_msgs=None):
    flashes = ''
    if flash_msgs:
        flashes = '<div class="flash-container">'
        for cat, msg in flash_msgs:
            flashes += f'<div class="flash flash-{cat}">{msg}<button class="flash-close" onclick="this.parentElement.remove()">×</button></div>'
        flashes += '</div>'
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title><style>{CSS}</style></head>
<body>{navbar_html()}<main class="container">{flashes}{content}</main>
<script>document.querySelectorAll('.flash').forEach(el=>setTimeout(()=>{{el.style.opacity='0';setTimeout(()=>el.remove(),300)}},5000));</script>
</body></html>'''

# ==============================================================================
# BASE DE DATOS
# ==============================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
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
            FOREIGN KEY (profesional_id) REFERENCES profesionales(id)
        );
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cita_id INTEGER,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            detalle TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha);
        CREATE INDEX IF NOT EXISTS idx_citas_prof ON citas(profesional_id);
        CREATE INDEX IF NOT EXISTS idx_citas_estado ON citas(estado);
    ''')
    admin = conn.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
    if not admin:
        conn.execute("INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?,?,?,?)",
            ('admin', generate_password_hash('admin123'), 'Administrador', 'admin'))
    count = conn.execute("SELECT COUNT(*) FROM profesionales").fetchone()[0]
    if count == 0:
        for i, (nombre, colores) in enumerate(PROF_PALETTE.items()):
            esp = 'PSICOLOGÍA'
            for area, profs in SPECIALTY_MAP.items():
                if nombre in profs: esp = area; break
            conn.execute("INSERT INTO profesionales (nombre, especialidad, color_bg, color_font, orden) VALUES (?,?,?,?,?)",
                (nombre, esp, colores['bg'], colores['font'], i))
    conn.commit()
    conn.close()

# ==============================================================================
# AUTENTICACIÓN
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session: return redirect('/login')
        if session.get('user_rol') != 'admin': return redirect('/')
        return f(*args, **kwargs)
    return decorated

# ==============================================================================
# MOTOR DE GENERACIÓN
# ==============================================================================
def parse_roster_text(text):
    result = {}
    for line in text.strip().split('\n'):
        if ':' not in line: continue
        parts = line.split(':', 1)
        name = parts[0].strip().upper()
        sched_text = parts[1].strip()
        matches = re.findall(r'[Dd]ía\s+(\d+)\s+([A-Za-z]+)', sched_text)
        schedule = {}
        for day, code in matches: schedule[int(day)] = code.upper()
        if schedule: result[name] = schedule
    return result

def _make_slots(start_str, n, duration, turno):
    slots = []
    curr = datetime.strptime(start_str, "%H:%M")
    for _ in range(n):
        end = curr + timedelta(minutes=duration)
        slots.append({'inicio': curr.strftime('%H:%M'), 'fin': end.strftime('%H:%M'), 'turno': turno})
        curr = end
    return slots

def generate_slots(conn, year, month, roster_text=None):
    profs = {r['nombre']: dict(r) for r in conn.execute("SELECT * FROM profesionales WHERE activo=1").fetchall()}
    if roster_text:
        parsed = parse_roster_text(roster_text)
    else:
        parsed = {}
        rows = conn.execute("SELECT r.dia, r.turno, p.nombre FROM roles_mensuales r JOIN profesionales p ON p.id=r.profesional_id WHERE r.anio=? AND r.mes=?", (year, month)).fetchall()
        for r in rows: parsed.setdefault(r['nombre'], {})[r['dia']] = r['turno']
    if not parsed: return 0
    num_days = calendar.monthrange(year, month)[1]
    existing = {}
    rows = conn.execute("SELECT c.*, p.nombre as prof_nombre FROM citas c JOIN profesionales p ON p.id=c.profesional_id WHERE c.fecha BETWEEN ? AND ? AND c.estado != 'Disponible'",
        (f"{year}-{month:02d}-01", f"{year}-{month:02d}-{num_days:02d}")).fetchall()
    for r in rows:
        key = (r['prof_nombre'], r['fecha'])
        existing.setdefault(key, []).append(dict(r))
    conn.execute("DELETE FROM citas WHERE fecha BETWEEN ? AND ?", (f"{year}-{month:02d}-01", f"{year}-{month:02d}-{num_days:02d}"))
    conn.execute("DELETE FROM roles_mensuales WHERE anio=? AND mes=?", (year, month))
    count = 0
    for day in range(1, num_days + 1):
        try: curr_date = datetime(year, month, day)
        except ValueError: continue
        for prof_name, schedule in parsed.items():
            if day not in schedule: continue
            prof_data = None
            for db_name, db_data in profs.items():
                n1 = prof_name.replace(" ", "").upper()
                n2 = db_name.replace(" ", "").upper()
                if n1 in n2 or n2 in n1: prof_data = db_data; break
            if not prof_data: continue
            shift = schedule[day]
            is_med = prof_data['especialidad'] in ('MEDICINA', 'PSIQUIATRÍA')
            date_str = curr_date.strftime('%Y-%m-%d')
            conn.execute("INSERT OR REPLACE INTO roles_mensuales (profesional_id, anio, mes, dia, turno) VALUES (?,?,?,?,?)",
                (prof_data['id'], year, month, day, shift))
            slots_to_create = []
            if shift in ('M', 'MT', 'GD'):
                start = "07:30"; n_slots = 8 if is_med else 7; dur = 40 if is_med else 45
                slots_to_create.extend(_make_slots(start, n_slots, dur, 'MAÑANA'))
            if shift in ('T', 'MT', 'GD'):
                start = "14:00" if is_med else "13:50"; n_slots = 7 if is_med else 6; dur = 40 if is_med else 45
                slots_to_create.extend(_make_slots(start, n_slots, dur, 'TARDE'))
            prev_appointments = existing.get((prof_data['nombre'], date_str), [])
            prev_by_order = sorted(prev_appointments, key=lambda x: x['hora_inicio'])
            for i, slot in enumerate(slots_to_create):
                pac=''; dni=''; cel=''; obs=''; estado='Disponible'; tipo=''; asist='Pendiente'; creado=None; modificado=None
                if i < len(prev_by_order):
                    prev = prev_by_order[i]; pac=prev['paciente']; dni=prev['dni']; cel=prev['celular']
                    obs=prev['observaciones']; estado=prev['estado']; tipo=prev['tipo_paciente']; asist=prev['asistencia']
                conn.execute("INSERT INTO citas (profesional_id,fecha,hora_inicio,hora_fin,turno,area,paciente,dni,celular,observaciones,estado,tipo_paciente,asistencia) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (prof_data['id'], date_str, slot['inicio'], slot['fin'], slot['turno'], prof_data['especialidad'], pac, dni, cel, obs, estado, tipo, asist))
                count += 1
    conn.commit()
    return count

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
# RUTAS
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM usuarios WHERE username=? AND activo=1", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_nombre'] = user['nombre']
            session['user_rol'] = user['rol']
            return redirect('/')
        error_html = '<div class="flash flash-danger" style="margin-bottom:1rem">Usuario o contraseña incorrectos</div>'
    else:
        error_html = ''

    return f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Login - Sistema de Citas</title><style>{CSS}</style></head><body>
<div class="login-wrapper"><div class="login-card">
<div class="login-header"><span class="login-icon">🏥</span><h1>Sistema de Citas</h1><p>Centro de Salud Mental</p></div>
{error_html}
<form method="POST" class="login-form">
<div class="form-group"><label for="username">Usuario</label><input type="text" id="username" name="username" required autofocus placeholder="Ingrese su usuario" class="form-input"></div>
<div class="form-group"><label for="password">Contraseña</label><input type="password" id="password" name="password" required placeholder="Ingrese su contraseña" class="form-input"></div>
<button type="submit" class="btn btn-primary btn-full">Ingresar</button>
</form>
<div class="login-footer"><small>Usuario inicial: <b>admin</b> / Contraseña: <b>admin123</b></small></div>
</div></div></body></html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def agenda():
    conn = get_db()
    prof_id = request.args.get('prof_id', '')
    fecha = request.args.get('fecha', '')
    profesionales = conn.execute("SELECT * FROM profesionales WHERE activo=1 ORDER BY orden").fetchall()

    # Build prof options
    prof_options = '<option value="">— Seleccionar profesional —</option>'
    for p in profesionales:
        sel = 'selected' if str(p['id']) == str(prof_id) else ''
        prof_options += f'<option value="{p["id"]}" {sel} style="background-color:{p["color_bg"]};color:{p["color_font"]}">{p["nombre"]} ({p["especialidad"]})</option>'

    # Build fecha options
    fecha_options = '<option value="">— Seleccionar fecha —</option>'
    if prof_id:
        rows = conn.execute("SELECT DISTINCT fecha FROM citas WHERE profesional_id=? ORDER BY fecha", (prof_id,)).fetchall()
        for r in rows:
            try:
                dt = datetime.strptime(r['fecha'], '%Y-%m-%d')
                dia_sem = DIAS_CORTO[dt.weekday()]
                label = f"{dt.day} {dia_sem} ({dt.strftime('%d/%m')})"
            except: label = r['fecha']
            sel = 'selected' if r['fecha'] == fecha else ''
            fecha_options += f'<option value="{r["fecha"]}" {sel}>{label}</option>'

    # Build citas table
    citas_html = ''
    if prof_id and fecha:
        citas = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.color_bg, p.color_font
            FROM citas c JOIN profesionales p ON p.id=c.profesional_id
            WHERE c.profesional_id=? AND c.fecha=? ORDER BY c.turno, c.hora_inicio""", (prof_id, fecha)).fetchall()

        if citas:
            # Date banner
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_info = f"{dt.day} {DIAS_ES[dt.weekday()]} - {dt.strftime('%d/%m/%Y')}"
            except: fecha_info = fecha
            total = len(citas)
            ocupados = sum(1 for c in citas if c['estado'] == 'Confirmado')
            citas_html += f'''<div class="date-banner"><strong>{fecha_info}</strong>
                <span class="badge badge-info">{total} cupos</span>
                <span class="badge badge-success">{total-ocupados} disponibles</span>
                <span class="badge badge-danger">{ocupados} ocupados</span></div>'''

            # Table
            citas_html += '''<div class="table-wrapper"><table class="citas-table"><thead><tr>
                <th>Turno</th><th>Hora</th><th>Paciente</th><th>DNI</th><th>Tipo</th><th>Estado</th><th>Asistencia</th><th>Acciones</th>
                </tr></thead><tbody>'''
            current_turno = ''
            for c in citas:
                if c['turno'] != current_turno:
                    current_turno = c['turno']
                    icon = '☀️' if c['turno'] == 'MAÑANA' else '🌙'
                    citas_html += f'<tr class="turno-divider"><td colspan="8"><span class="turno-label">{icon} {c["turno"]}</span></td></tr>'

                row_class = 'row-ocupado' if c['estado'] == 'Confirmado' else 'row-disponible'
                style = f'border-left:4px solid {c["color_bg"]};' if c['estado'] == 'Confirmado' else ''

                # Paciente cell
                if c['estado'] == 'Confirmado':
                    pac_cell = f'<span class="paciente-nombre">{c["paciente"]}</span>'
                    if c['celular']: pac_cell += f'<br><small class="text-muted">📱 {c["celular"]}</small>'
                    if c['observaciones']: pac_cell += f'<br><small class="text-muted">📝 {c["observaciones"]}</small>'
                else:
                    pac_cell = '<span class="text-available">Disponible</span>'

                # Tipo badge
                tipo_html = ''
                if c['tipo_paciente']:
                    badge_class = 'badge-new' if c['tipo_paciente'] == 'NUEVO' else 'badge-cont'
                    tipo_html = f'<span class="badge {badge_class}">{c["tipo_paciente"]}</span>'

                # Status
                status_class = 'status-confirmado' if c['estado'] == 'Confirmado' else 'status-disponible'
                status_html = f'<span class="status-dot {status_class}"></span>{c["estado"]}'

                # Asistencia
                asist_html = ''
                if c['estado'] == 'Confirmado':
                    a_active = 'btn-asist-active' if c['asistencia'] == 'Asistió' else ''
                    n_active = 'btn-asist-no-active' if c['asistencia'] == 'No asistió' else ''
                    asist_html = f'''<div class="asistencia-btns">
                        <button class="btn-asist {a_active}" onclick="marcarAsistencia({c['id']},'Asistió')" title="Asistió">✅</button>
                        <button class="btn-asist {n_active}" onclick="marcarAsistencia({c['id']},'No asistió')" title="No asistió">❌</button></div>'''

                # Actions
                if c['estado'] == 'Disponible':
                    action = f'<button class="btn btn-sm btn-success" onclick="openModal({c["id"]},\'{c["hora_inicio"]} - {c["hora_fin"]}\')">➕ Agendar</button>'
                else:
                    action = f'<form method="POST" action="/cita/eliminar/{c["id"]}" onsubmit="return confirm(\'¿Eliminar cita de {c["paciente"]}?\')"><button type="submit" class="btn btn-sm btn-danger">🗑️</button></form>'

                citas_html += f'''<tr class="cita-row {row_class}" style="{style}">
                    <td class="td-turno">{c['turno']}</td>
                    <td class="td-hora"><strong>{c['hora_inicio']} - {c['hora_fin']}</strong></td>
                    <td>{pac_cell}</td><td>{c['dni'] if c['estado']=='Confirmado' else ''}</td>
                    <td>{tipo_html}</td><td>{status_html}</td><td>{asist_html}</td><td>{action}</td></tr>'''

            citas_html += '</tbody></table></div>'
        else:
            citas_html = '<div class="empty-state"><p>No hay cupos para esta combinación.</p></div>'
    elif not prof_id:
        citas_html = '<div class="empty-state"><div class="empty-icon">📋</div><h3>Seleccione un profesional para ver su agenda</h3><p>Use los filtros de arriba para comenzar</p></div>'

    conn.close()

    content = f'''<div class="page-header"><h2>📅 Agenda de Citas</h2></div>
    <div class="card" style="padding:1rem">
        <div class="filter-row">
            <div class="filter-group"><label>Profesional</label>
                <select id="sel-prof" class="form-select" onchange="onProfChange(this.value)">{prof_options}</select></div>
            <div class="filter-group"><label>Fecha</label>
                <select id="sel-fecha" class="form-select" onchange="onFechaChange(this.value)">{fecha_options}</select></div>
        </div>
    </div>
    {citas_html}
    <div id="modal-agendar" class="modal" style="display:none">
        <div class="modal-content">
            <div class="modal-header"><h3>➕ Agendar Cita</h3><button class="modal-close" onclick="closeModal()">×</button></div>
            <form method="POST" action="/cita/agendar">
                <input type="hidden" name="cita_id" id="modal-cita-id">
                <div class="modal-body">
                    <p id="modal-hora" class="modal-hora-display"></p>
                    <div class="form-group"><label>Paciente *</label><input type="text" name="paciente" required class="form-input" placeholder="Nombre completo"></div>
                    <div class="form-row">
                        <div class="form-group"><label>DNI</label><input type="text" name="dni" class="form-input" maxlength="8" placeholder="12345678"></div>
                        <div class="form-group"><label>Celular</label><input type="text" name="celular" class="form-input" maxlength="9" placeholder="987654321"></div>
                    </div>
                    <div class="form-group"><label>Tipo de paciente</label><select name="tipo_paciente" class="form-select"><option value="NUEVO">NUEVO</option><option value="CONTINUADOR">CONTINUADOR</option></select></div>
                    <div class="form-group"><label>Observaciones</label><input type="text" name="observaciones" class="form-input" placeholder="Opcional"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
                    <button type="submit" class="btn btn-success">💾 Agendar</button>
                </div>
            </form>
        </div>
    </div>
    <script>
    function onProfChange(v){{if(v)fetch('/api/fechas/'+v).then(r=>r.json()).then(d=>{{let s=document.getElementById('sel-fecha');s.innerHTML='<option value="">— Seleccionar fecha —</option>';d.forEach(f=>{{let o=document.createElement('option');o.value=f.value;o.textContent=f.label;s.appendChild(o)}})}})}};
    function onFechaChange(f){{let p=document.getElementById('sel-prof').value;if(p&&f)window.location.href='/?prof_id='+p+'&fecha='+f}};
    function openModal(id,hora){{document.getElementById('modal-cita-id').value=id;document.getElementById('modal-hora').textContent='🕐 '+hora;document.getElementById('modal-agendar').style.display='flex'}};
    function closeModal(){{document.getElementById('modal-agendar').style.display='none'}};
    function marcarAsistencia(id,estado){{fetch('/cita/asistencia/'+id+'/'+encodeURIComponent(estado),{{method:'POST'}}).then(()=>location.reload())}};
    document.getElementById('modal-agendar')?.addEventListener('click',function(e){{if(e.target===this)closeModal()}});
    </script>'''

    flash_msgs = session.pop('_flashes', [])
    return page('Agenda - Sistema de Citas', content, flash_msgs)

@app.route('/api/fechas/<int:prof_id>')
@login_required
def api_fechas(prof_id):
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT fecha FROM citas WHERE profesional_id=? ORDER BY fecha", (prof_id,)).fetchall()
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
        return redirect(request.referrer or '/')
    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if not cita or cita['estado'] != 'Disponible':
        flash('Cupo no disponible', 'warning')
        conn.close()
        return redirect(request.referrer or '/')
    conn.execute("UPDATE citas SET paciente=?, dni=?, celular=?, observaciones=?, estado='Confirmado', tipo_paciente=?, creado_por=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?",
        (paciente, dni, celular, obs, tipo, session['user_id'], session['user_id'], cita_id))
    conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], 'AGENDAR', f'Paciente: {paciente} | DNI: {dni}'))
    conn.commit(); conn.close()
    flash(f'Cita agendada: {paciente}', 'success')
    return redirect(request.referrer or '/')

@app.route('/cita/eliminar/<int:cita_id>', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if cita and cita['estado'] != 'Disponible':
        conn.execute("UPDATE citas SET paciente='',dni='',celular='',observaciones='',estado='Disponible',tipo_paciente='',asistencia='Pendiente',modificado_por=?,modificado_en=CURRENT_TIMESTAMP WHERE id=?",
            (session['user_id'], cita_id))
        conn.execute("INSERT INTO historial (cita_id,usuario_id,accion,detalle) VALUES (?,?,?,?)",
            (cita_id, session['user_id'], 'ELIMINAR', f'Eliminado: {cita["paciente"]}'))
        conn.commit()
        flash('Cita eliminada', 'info')
    conn.close()
    return redirect(request.referrer or '/')

@app.route('/cita/asistencia/<int:cita_id>/<estado>', methods=['POST'])
@login_required
def marcar_asistencia(cita_id, estado):
    if estado not in ('Asistió', 'No asistió', 'Pendiente'): abort(400)
    conn = get_db()
    conn.execute("UPDATE citas SET asistencia=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?", (estado, session['user_id'], cita_id))
    conn.execute("INSERT INTO historial (cita_id,usuario_id,accion,detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], 'ASISTENCIA', f'Marcado como: {estado}'))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/generar', methods=['GET', 'POST'])
@admin_required
def generar():
    if request.method == 'POST':
        year = int(request.form.get('year', datetime.now().year))
        month = int(request.form.get('month', datetime.now().month))
        roster_text = request.form.get('roster_text', '')
        if not roster_text.strip():
            flash('El texto del rol no puede estar vacío', 'danger')
            return redirect('/generar')
        conn = get_db()
        count = generate_slots(conn, year, month, roster_text)
        conn.close()
        flash(f'✅ Generados {count} cupos para {calendar.month_name[month]} {year}', 'success')
        return redirect(f'/?year={year}&month={month}')

    meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    month_opts = ''.join([f'<option value="{i+1}" {"selected" if i+1==datetime.now().month else ""}>{m}</option>' for i, m in enumerate(meses)])

    content = f'''<div class="page-header"><h2>⚙️ Generar Calendario Mensual</h2><p class="text-muted" style="margin-top:.25rem;font-size:.9rem">Ingrese el rol mensual para generar los cupos de citas</p></div>
    <div class="card"><form method="POST">
        <div class="form-row">
            <div class="form-group"><label>Año</label><input type="number" name="year" value="{datetime.now().year}" class="form-input" min="2024" max="2030"></div>
            <div class="form-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
        </div>
        <div class="form-group"><label>Texto del Rol Mensual</label>
            <textarea name="roster_text" class="form-textarea" rows="16">{get_default_roster()}</textarea>
            <small class="form-help">Formato: NOMBRE: Día X TURNO. Turnos: M=Mañana, T=Tarde, MT=Mañana+Tarde, GD=Guardia Diurna.<br>⚠️ Si ya existen citas agendadas, se migrarán automáticamente a los nuevos cupos.</small>
        </div>
        <div class="form-actions"><button type="submit" class="btn btn-danger btn-lg" onclick="return confirm('¿Generar cupos? Las citas existentes se migrarán al nuevo horario.')">🔄 REGENERAR CALENDARIO</button></div>
    </form></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Generar - Sistema de Citas', content, flash_msgs)

@app.route('/profesionales')
@admin_required
def profesionales():
    conn = get_db()
    profs = conn.execute("SELECT * FROM profesionales ORDER BY orden").fetchall()
    conn.close()

    rows = ''
    for p in profs:
        inactive = 'row-inactive' if not p['activo'] else ''
        status_badge = f'<span class="badge badge-success">Activo</span>' if p['activo'] else '<span class="badge badge-danger">Inactivo</span>'
        btn_text = '⏸️ Desactivar' if p['activo'] else '▶️ Activar'
        btn_class = 'btn-warning' if p['activo'] else 'btn-success'
        rows += f'''<tr class="{inactive}">
            <td><span class="color-swatch" style="background:{p['color_bg']};color:{p['color_font']}">Aa</span></td>
            <td><strong>{p['nombre']}</strong></td><td>{p['especialidad']}</td><td>{status_badge}</td>
            <td><form method="POST" action="/profesional/toggle/{p['id']}" style="display:inline"><button type="submit" class="btn btn-sm {btn_class}">{btn_text}</button></form></td></tr>'''

    content = f'''<div class="page-header"><h2>👥 Gestión de Profesionales</h2></div>
    <div class="card"><h3>Agregar Profesional</h3>
    <form method="POST" action="/profesional/nuevo">
        <div class="form-row">
            <div class="form-group" style="flex:2"><label>Nombre completo</label><input type="text" name="nombre" class="form-input" required placeholder="APELLIDO APELLIDO NOMBRE NOMBRE"></div>
            <div class="form-group"><label>Especialidad</label><select name="especialidad" class="form-select"><option value="PSICOLOGÍA">PSICOLOGÍA</option><option value="MEDICINA">MEDICINA</option><option value="PSIQUIATRÍA">PSIQUIATRÍA</option></select></div>
            <div class="form-group"><label>Color fondo</label><input type="color" name="color_bg" value="#CCCCCC" class="form-color"></div>
            <div class="form-group"><label>Color texto</label><select name="color_font" class="form-select"><option value="black">Negro</option><option value="white">Blanco</option></select></div>
        </div>
        <button type="submit" class="btn btn-success">➕ Agregar</button>
    </form></div>
    <div class="card"><h3>Profesionales Registrados</h3>
    <div class="table-wrapper"><table class="citas-table"><thead><tr><th>Color</th><th>Nombre</th><th>Especialidad</th><th>Estado</th><th>Acciones</th></tr></thead>
    <tbody>{rows}</tbody></table></div></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Profesionales - Sistema de Citas', content, flash_msgs)

@app.route('/profesional/nuevo', methods=['POST'])
@admin_required
def nuevo_profesional():
    nombre = request.form.get('nombre', '').strip().upper()
    esp = request.form.get('especialidad', 'PSICOLOGÍA')
    color_bg = request.form.get('color_bg', '#CCCCCC')
    color_font = request.form.get('color_font', 'black')
    if not nombre:
        flash('El nombre es obligatorio', 'danger')
        return redirect('/profesionales')
    conn = get_db()
    try:
        max_orden = conn.execute("SELECT MAX(orden) FROM profesionales").fetchone()[0] or 0
        conn.execute("INSERT INTO profesionales (nombre, especialidad, color_bg, color_font, orden) VALUES (?,?,?,?,?)",
            (nombre, esp, color_bg, color_font, max_orden + 1))
        conn.commit()
        flash(f'Profesional {nombre} agregado', 'success')
    except sqlite3.IntegrityError:
        flash('Ya existe un profesional con ese nombre', 'warning')
    conn.close()
    return redirect('/profesionales')

@app.route('/profesional/toggle/<int:prof_id>', methods=['POST'])
@admin_required
def toggle_profesional(prof_id):
    conn = get_db()
    prof = conn.execute("SELECT * FROM profesionales WHERE id=?", (prof_id,)).fetchone()
    if prof:
        conn.execute("UPDATE profesionales SET activo=? WHERE id=?", (0 if prof['activo'] else 1, prof_id))
        conn.commit()
    conn.close()
    return redirect('/profesionales')

@app.route('/usuarios')
@admin_required
def usuarios():
    conn = get_db()
    users = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
    conn.close()
    rows = ''
    for u in users:
        inactive = 'row-inactive' if not u['activo'] else ''
        role_badge = f'<span class="badge badge-admin">ADMIN</span>' if u['rol'] == 'admin' else '<span class="badge badge-info">OPERADOR</span>'
        status_badge = '<span class="badge badge-success">Activo</span>' if u['activo'] else '<span class="badge badge-danger">Inactivo</span>'
        action = ''
        if u['id'] != session.get('user_id'):
            btn = '⏸️' if u['activo'] else '▶️'
            btn_class = 'btn-warning' if u['activo'] else 'btn-success'
            action = f'<form method="POST" action="/usuario/toggle/{u["id"]}" style="display:inline"><button type="submit" class="btn btn-sm {btn_class}">{btn}</button></form>'
        else:
            action = '<small class="text-muted">(Usted)</small>'
        rows += f'<tr class="{inactive}"><td>{u["id"]}</td><td><strong>{u["username"]}</strong></td><td>{u["nombre"]}</td><td>{role_badge}</td><td>{status_badge}</td><td>{action}</td></tr>'

    content = f'''<div class="page-header"><h2>🔑 Gestión de Usuarios</h2></div>
    <div class="card"><h3>Crear Usuario</h3>
    <form method="POST" action="/usuario/nuevo">
        <div class="form-row">
            <div class="form-group"><label>Usuario</label><input type="text" name="username" class="form-input" required placeholder="usuario"></div>
            <div class="form-group"><label>Contraseña</label><input type="password" name="password" class="form-input" required></div>
            <div class="form-group"><label>Nombre</label><input type="text" name="nombre" class="form-input" required placeholder="Nombre completo"></div>
            <div class="form-group"><label>Rol</label><select name="rol" class="form-select"><option value="operador">Operador</option><option value="admin">Administrador</option></select></div>
        </div>
        <button type="submit" class="btn btn-success">➕ Crear Usuario</button>
    </form></div>
    <div class="card"><h3>Usuarios Registrados</h3>
    <div class="table-wrapper"><table class="citas-table"><thead><tr><th>ID</th><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
    <tbody>{rows}</tbody></table></div></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Usuarios - Sistema de Citas', content, flash_msgs)

@app.route('/usuario/nuevo', methods=['POST'])
@admin_required
def nuevo_usuario():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    nombre = request.form.get('nombre', '').strip()
    rol = request.form.get('rol', 'operador')
    if not username or not password:
        flash('Usuario y contraseña son obligatorios', 'danger')
        return redirect('/usuarios')
    conn = get_db()
    try:
        conn.execute("INSERT INTO usuarios (username, password_hash, nombre, rol) VALUES (?,?,?,?)",
            (username, generate_password_hash(password), nombre, rol))
        conn.commit()
        flash(f'Usuario {username} creado', 'success')
    except sqlite3.IntegrityError:
        flash('Ya existe ese nombre de usuario', 'warning')
    conn.close()
    return redirect('/usuarios')

@app.route('/usuario/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_usuario(user_id):
    if user_id == session.get('user_id'):
        flash('No puede desactivar su propia cuenta', 'danger')
        return redirect('/usuarios')
    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if user:
        conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (0 if user['activo'] else 1, user_id))
        conn.commit()
    conn.close()
    return redirect('/usuarios')

@app.route('/reportes')
@login_required
def reportes():
    conn = get_db()
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    stats = conn.execute("""SELECT COUNT(*) as total,
        SUM(CASE WHEN estado='Confirmado' THEN 1 ELSE 0 END) as confirmados,
        SUM(CASE WHEN estado='Disponible' THEN 1 ELSE 0 END) as disponibles,
        SUM(CASE WHEN asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
        SUM(CASE WHEN tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores
        FROM citas WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=?""", (str(year), f"{month:02d}")).fetchone()

    by_prof = conn.execute("""SELECT p.nombre, p.color_bg, p.color_font, p.especialidad,
        COUNT(*) as total,
        SUM(CASE WHEN c.estado='Confirmado' THEN 1 ELSE 0 END) as confirmados,
        SUM(CASE WHEN c.asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN c.asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN c.tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
        SUM(CASE WHEN c.tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=?
        GROUP BY p.id ORDER BY p.orden""", (str(year), f"{month:02d}")).fetchall()

    historial = conn.execute("""SELECT h.*, u.nombre as usuario_nombre, c.paciente, c.fecha, p.nombre as prof_nombre
        FROM historial h LEFT JOIN usuarios u ON u.id=h.usuario_id LEFT JOIN citas c ON c.id=h.cita_id
        LEFT JOIN profesionales p ON p.id=c.profesional_id ORDER BY h.fecha_hora DESC LIMIT 50""").fetchall()
    conn.close()

    meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    month_opts = ''.join([f'<option value="{i+1}" {"selected" if i+1==month else ""}>{m}</option>' for i, m in enumerate(meses)])

    total = stats['total'] or 0
    confirmados = stats['confirmados'] or 0
    ocupacion = round(confirmados / total * 100, 1) if total else 0

    stats_html = f'''<div class="stats-grid">
        <div class="stat-card stat-total"><div class="stat-number">{total}</div><div class="stat-label">Total Cupos</div></div>
        <div class="stat-card stat-confirmed"><div class="stat-number">{confirmados}</div><div class="stat-label">Confirmados</div></div>
        <div class="stat-card stat-available"><div class="stat-number">{stats['disponibles'] or 0}</div><div class="stat-label">Disponibles</div></div>
        <div class="stat-card stat-attended"><div class="stat-number">{stats['asistieron'] or 0}</div><div class="stat-label">Asistieron ✅</div></div>
        <div class="stat-card stat-absent"><div class="stat-number">{stats['no_asistieron'] or 0}</div><div class="stat-label">No asistieron ❌</div></div>
        <div class="stat-card stat-new"><div class="stat-number">{stats['nuevos'] or 0}</div><div class="stat-label">Nuevos</div></div>
        <div class="stat-card stat-cont"><div class="stat-number">{stats['continuadores'] or 0}</div><div class="stat-label">Continuadores</div></div>
        <div class="stat-card stat-rate"><div class="stat-number">{ocupacion}%</div><div class="stat-label">Ocupación</div></div>
    </div>'''

    prof_rows = ''
    for p in by_prof:
        pct = round((p['confirmados'] or 0) / p['total'] * 100, 1) if p['total'] else 0
        prof_rows += f'''<tr><td><span class="prof-chip" style="background:{p['color_bg']};color:{p['color_font']}">{p['nombre']}</span></td>
            <td>{p['especialidad']}</td><td><strong>{p['total']}</strong></td><td>{p['confirmados'] or 0}</td>
            <td class="text-success">{p['asistieron'] or 0}</td><td class="text-danger">{p['no_asistieron'] or 0}</td>
            <td>{p['nuevos'] or 0}</td><td>{p['continuadores'] or 0}</td>
            <td><div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div><small>{pct}%</small></td></tr>'''

    hist_rows = ''
    for h in historial:
        badge_class = 'badge-success' if h['accion'] == 'AGENDAR' else 'badge-danger' if h['accion'] == 'ELIMINAR' else 'badge-info'
        hist_rows += f'''<tr><td><small>{h['fecha_hora']}</small></td><td>{h['usuario_nombre'] or '—'}</td>
            <td><span class="badge {badge_class}">{h['accion']}</span></td>
            <td><small>{h['prof_nombre'] or '—'}</small></td><td><small>{h['detalle'] or ''}</small></td></tr>'''
    if not historial:
        hist_rows = '<tr><td colspan="5" class="text-center">Sin registros</td></tr>'

    content = f'''<div class="page-header"><h2>📊 Reportes y Estadísticas</h2></div>
    <div class="card" style="padding:1rem"><form method="GET" class="filter-row">
        <div class="filter-group"><label>Año</label><input type="number" name="year" value="{year}" class="form-input" min="2024" max="2030"></div>
        <div class="filter-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
        <div class="filter-group" style="align-self:flex-end"><button type="submit" class="btn btn-primary">🔍 Consultar</button></div>
    </form></div>
    {stats_html}
    <div class="card"><h3>📋 Por Profesional</h3><div class="table-wrapper"><table class="citas-table"><thead><tr>
        <th>Profesional</th><th>Especialidad</th><th>Cupos</th><th>Confirmados</th><th>Asistieron</th><th>No asistieron</th><th>Nuevos</th><th>Continuadores</th><th>% Ocupación</th>
    </tr></thead><tbody>{prof_rows}</tbody></table></div></div>
    <div class="card"><h3>📜 Historial Reciente</h3><div class="table-wrapper"><table class="citas-table"><thead><tr>
        <th>Fecha/Hora</th><th>Usuario</th><th>Acción</th><th>Profesional</th><th>Detalle</th>
    </tr></thead><tbody>{hist_rows}</tbody></table></div></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Reportes - Sistema de Citas', content, flash_msgs)

@app.route('/exportar')
@login_required
def exportar_excel():
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    conn = get_db()
    rows = conn.execute("""SELECT c.fecha, c.turno, c.area, p.nombre as profesional,
        c.hora_inicio, c.hora_fin, c.paciente, c.dni, c.celular, c.observaciones, c.estado,
        c.tipo_paciente, c.asistencia, p.color_bg, p.color_font
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=?
        ORDER BY c.fecha, c.turno, p.orden, c.hora_inicio""", (str(year), f"{month:02d}")).fetchall()
    conn.close()
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('AGENDA')
    fmt_h = wb.add_format({'bold': True, 'bg_color': '#404040', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    fmt_date = wb.add_format({'bg_color': '#000000', 'font_color': 'white', 'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    headers = ['FECHA', 'TURNO', 'ÁREA', 'PROFESIONAL', 'HORA', 'PACIENTE', 'DNI', 'CELULAR', 'OBSERVACIONES', 'ESTADO', 'TIPO', 'ASISTENCIA']
    for i, h in enumerate(headers): ws.write(0, i, h, fmt_h)
    ws.set_column(0, 0, 12); ws.set_column(1, 2, 12); ws.set_column(3, 3, 35); ws.set_column(4, 4, 15); ws.set_column(5, 5, 35)
    fmt_cache = {}
    for i, row in enumerate(rows):
        r = i + 1; row = dict(row)
        key = (row['color_bg'], row['color_font'])
        if key not in fmt_cache:
            fmt_cache[key] = {
                'c': wb.add_format({'bg_color': key[0], 'font_color': key[1], 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
                'l': wb.add_format({'bg_color': key[0], 'font_color': key[1], 'border': 1, 'align': 'left', 'valign': 'vcenter', 'indent': 1}),
            }
        try:
            dt = datetime.strptime(row['fecha'], '%Y-%m-%d'); fecha_vis = f"{dt.day} {DIAS_CORTO[dt.weekday()]}"
        except: fecha_vis = row['fecha']
        hora = f"{row['hora_inicio']} - {row['hora_fin']}"
        fc = fmt_cache[key]['c']; fl = fmt_cache[key]['l']
        ws.write(r, 0, fecha_vis, fmt_date); ws.write(r, 1, row['turno'], fc); ws.write(r, 2, row['area'], fc)
        ws.write(r, 3, row['profesional'], fl); ws.write(r, 4, hora, fc); ws.write(r, 5, row['paciente'], fl)
        ws.write(r, 6, row['dni'], fc); ws.write(r, 7, row['celular'], fc); ws.write(r, 8, row['observaciones'], fl)
        ws.write(r, 9, row['estado'], fc); ws.write(r, 10, row['tipo_paciente'], fc); ws.write(r, 11, row['asistencia'], fc)
    wb.close(); output.seek(0)
    filename = f"Agenda_{calendar.month_name[month]}_{year}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==============================================================================
# INICIALIZACIÓN
# ==============================================================================
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
