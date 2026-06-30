#!/usr/bin/env python3
"""
SISTEMA DE CITAS MÉDICAS v3.0
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
DB_PATH = os.path.join('/data', 'citas.db') if os.path.isdir('/data') else os.path.join('/tmp', 'citas.db')

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
    "TERAPIA DE LENGUAJE": ["CHOQUE AVILES ANA LUZ", "HUAMANI AÑAMURO MERYLIN NATALY"],
    "TERAPIA OCUPACIONAL": ["COLQUEHUANCA PUMA LUZ MARY"],
}

DIAS_ES = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']
DIAS_CORTO = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
MESES_ES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

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
.row-app{border-left:4px solid #c62828;background:#ffebee !important}
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
.btn-asist-active{border-color:var(--accent);background:#43a047;box-shadow:0 0 0 3px rgba(67,160,71,.35);transform:scale(1.05)}
.btn-asist-no-active{border-color:var(--danger);background:#e53935;box-shadow:0 0 0 3px rgba(229,57,53,.35);transform:scale(1.05)}
.asistencia-btns.pendiente{padding:3px 5px;border-radius:6px;background:#fff3e0;box-shadow:0 0 0 2px #ff9800;animation:pulse-asist 1.6s ease-in-out infinite}
@keyframes pulse-asist{0%,100%{box-shadow:0 0 0 2px #ff9800}50%{box-shadow:0 0 0 4px rgba(255,152,0,.5)}}
@keyframes bannerPulse{0%,100%{box-shadow:0 3px 10px rgba(245,124,0,.4)}50%{box-shadow:0 3px 18px rgba(245,124,0,.7)}}
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
.modal-content{background:#fff;border-radius:var(--radius);box-shadow:0 4px 12px rgba(0,0,0,.1);width:100%;max-width:520px;max-height:90vh;overflow-y:auto}
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
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-top:.5rem}
.cal-header{background:var(--primary);color:#fff;padding:.3rem;text-align:center;font-size:.7rem;font-weight:700}
.cal-day{padding:.3rem;text-align:center;font-size:.75rem;border:1px solid var(--border);min-height:32px;cursor:pointer;border-radius:3px;transition:all .15s}
.cal-day:hover{transform:scale(1.05);box-shadow:var(--shadow)}
.cal-day.empty{border:none;cursor:default}
.cal-day.empty:hover{transform:none;box-shadow:none}
.cal-day.turno-mt{background:#1565c0;color:#fff;font-weight:700}
.cal-day.turno-gd{background:#1565c0;color:#fff;font-weight:700}
.cal-day.turno-m{background:#ff8f00;color:#fff;font-weight:700}
.cal-day.turno-t{background:#2e7d32;color:#fff;font-weight:700}
.cal-day.selected{outline:3px solid var(--danger);outline-offset:1px}
.cal-legend{display:flex;gap:1rem;margin-top:.5rem;font-size:.75rem;flex-wrap:wrap}
.cal-legend span{display:inline-flex;align-items:center;gap:.3rem}
.cal-legend-dot{width:14px;height:14px;border-radius:3px;display:inline-block}
.sihce-tag{background:#ff6f00;color:#fff;padding:.1rem .4rem;border-radius:3px;font-size:.7rem;font-weight:700}
@media(max-width:768px){.navbar{flex-wrap:wrap;height:auto;padding:.5rem 1rem;gap:.5rem}.nav-links{order:3;width:100%;padding-bottom:.5rem}.container{padding:1rem}.filter-row,.form-row{flex-direction:column}.filter-group{min-width:unset}.stats-grid{grid-template-columns:repeat(2,1fr)}.date-banner{flex-direction:column;align-items:flex-start}}
@media print{.navbar,.btn,.no-print{display:none!important}.container{padding:0}.card{box-shadow:none;border:1px solid #ccc}}
"""

ESPECIALIDADES_OPTIONS = '<option value="PSICOLOGÍA">PSICOLOGÍA</option><option value="MEDICINA">MEDICINA</option><option value="PSIQUIATRÍA">PSIQUIATRÍA</option><option value="PSIQUIATRÍA - LOCACIÓN">PSIQUIATRÍA - LOCACIÓN</option><option value="TERAPIA OCUPACIONAL">TERAPIA OCUPACIONAL</option><option value="TERAPIA DE LENGUAJE">TERAPIA DE LENGUAJE</option><option value="SIHCE">SIHCE</option>'

# ==============================================================================
# HTML HELPERS
# ==============================================================================
def navbar_html():
    if 'user_id' not in session:
        return ''
    is_admin = session.get('user_rol') == 'admin'
    is_lector = session.get('user_rol') == 'lector'
    admin_links = ''
    if is_admin:
        admin_links = '''
        <a href="/cambiar_turno" class="nav-link">🔄 Cambiar Turno</a>
        <a href="/unir_turnos" class="nav-link">🔗 Unir Turnos</a>
        <a href="/historial" class="nav-link">📜 Historial</a>
        <a href="/generar" class="nav-link">⚙️ Generar</a>
        <a href="/profesionales" class="nav-link">👥 Profesionales</a>
        <a href="/usuarios" class="nav-link">🔑 Usuarios</a>
        '''
    excel_link = '' if is_lector else '<a href="/exportar_form" class="nav-link">📥 Excel</a>'
    return f'''<nav class="navbar">
        <div class="nav-brand"><span style="font-size:1.4rem">🏥</span><span class="nav-title">SISTEMA DE CITAS</span></div>
        <div class="nav-links">
            <a href="/" class="nav-link">📅 Agenda</a>
            <a href="/buscar" class="nav-link">🔍 Buscar</a>
            <a href="/reporte_diario" class="nav-link">📋 Reporte Diario</a>
            {admin_links}
            <a href="/reportes" class="nav-link">📊 Reportes</a>
            <a href="/inasistencias" class="nav-link">📉 Inasistencias</a>
            {excel_link}
        </div>
        <div class="nav-user">
            <span class="user-badge">{session.get('user_nombre','')}</span>
            <a href="/logout" class="btn-logout">Salir</a>
        </div>
    </nav>'''

def page(title, content, flash_msgs=None, show_asist_banner=False):
    flashes = ''
    if flash_msgs:
        flashes = '<div class="flash-container">'
        for cat, msg in flash_msgs:
            flashes += f'<div class="flash flash-{cat}">{msg}<button class="flash-close" onclick="this.parentElement.remove()">×</button></div>'
        flashes += '</div>'
    # Banner de recordatorio de asistencia (solo agenda y reporte diario, no lectores)
    banner = ''
    if show_asist_banner and session.get('user_rol') != 'lector':
        banner = '''<div id="asist-banner" style="display:none;background:linear-gradient(90deg,#ff9800,#f57c00);color:#fff;padding:1rem 1.25rem;border-radius:10px;margin-bottom:1rem;box-shadow:0 3px 10px rgba(245,124,0,.4);align-items:center;gap:1rem;animation:bannerPulse 2s ease-in-out infinite">
            <span style="font-size:2rem;line-height:1">⏰</span>
            <div style="flex:1">
                <div style="font-size:1.15rem;font-weight:800;letter-spacing:.3px">¡RECUERDE MARCAR LA ASISTENCIA!</div>
                <div style="font-size:.95rem;opacity:.95;margin-top:2px">Marque la asistencia de los usuarios cada 2 horas para mantener el registro actualizado.</div>
            </div>
            <button onclick="cerrarAsistBanner()" style="background:rgba(255,255,255,.25);border:none;color:#fff;width:36px;height:36px;border-radius:50%;font-size:1.4rem;cursor:pointer;font-weight:bold;line-height:1;flex-shrink:0" title="Cerrar">×</button>
        </div>
        <script>
        function cerrarAsistBanner(){
            document.getElementById("asist-banner").style.display="none";
            try{sessionStorage.setItem("asistBannerCerrado", Date.now().toString());}catch(e){}
        }
        (function(){
            var banner=document.getElementById("asist-banner");
            if(!banner)return;
            var cerrado=null;
            try{cerrado=sessionStorage.getItem("asistBannerCerrado");}catch(e){}
            var dosHoras=2*60*60*1000;
            var mostrar=true;
            if(cerrado){
                var transcurrido=Date.now()-parseInt(cerrado);
                if(transcurrido<dosHoras)mostrar=false;
            }
            if(mostrar)banner.style.display="flex";
            // Reaparecer automáticamente cada 2 horas
            setInterval(function(){
                banner.style.display="flex";
                try{sessionStorage.removeItem("asistBannerCerrado");}catch(e){}
            }, dosHoras);
        })();
        </script>'''
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title><style>{CSS}</style></head>
<body>{navbar_html()}<main class="container">{flashes}{banner}{content}</main>
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
            edad TEXT DEFAULT '',
            celular TEXT DEFAULT '',
            observaciones TEXT DEFAULT '',
            estado TEXT DEFAULT 'Disponible',
            tipo_paciente TEXT DEFAULT '',
            actividad_app TEXT DEFAULT '',
            asistencia TEXT DEFAULT 'Pendiente',
            sihce INTEGER DEFAULT 0,
            sihce_prof_id INTEGER DEFAULT 0,
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
    # Add sihce column if missing (for upgrades)
    try:
        conn.execute("SELECT sihce FROM citas LIMIT 1")
    except:
        conn.execute("ALTER TABLE citas ADD COLUMN sihce INTEGER DEFAULT 0")
    # Add edad column if missing
    try:
        conn.execute("SELECT edad FROM citas LIMIT 1")
    except:
        conn.execute("ALTER TABLE citas ADD COLUMN edad TEXT DEFAULT ''")
    # Add actividad_app column if missing
    try:
        conn.execute("SELECT actividad_app FROM citas LIMIT 1")
    except:
        conn.execute("ALTER TABLE citas ADD COLUMN actividad_app TEXT DEFAULT ''")
    # Add sihce_prof_id column if missing
    try:
        conn.execute("SELECT sihce_prof_id FROM citas LIMIT 1")
    except:
        conn.execute("ALTER TABLE citas ADD COLUMN sihce_prof_id INTEGER DEFAULT 0")
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
        conn = get_db()
        user = conn.execute("SELECT activo FROM usuarios WHERE id=?", (session['user_id'],)).fetchone()
        conn.close()
        if not user or not user['activo']:
            session.clear()
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
# MOTOR DE GENERACIÓN - HORARIOS CORREGIDOS
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
            is_med = prof_data['especialidad'] in ('MEDICINA', 'PSIQUIATRÍA', 'SIHCE')
            is_to = prof_data['especialidad'] == 'TERAPIA OCUPACIONAL'
            is_loc = prof_data['especialidad'] == 'PSIQUIATRÍA - LOCACIÓN'
            date_str = curr_date.strftime('%Y-%m-%d')
            conn.execute("INSERT OR REPLACE INTO roles_mensuales (profesional_id, anio, mes, dia, turno) VALUES (?,?,?,?,?)",
                (prof_data['id'], year, month, day, shift))
            slots_to_create = []
            if is_loc:
                # PSIQUIATRÍA - LOCACIÓN: 10 pacientes mañana (7:30-13:00, 33 min) + 10 tarde (14:00-19:30)
                if shift == 'M':
                    slots_to_create.extend(_make_slots("07:30", 10, 33, 'MAÑANA'))
                elif shift == 'T':
                    slots_to_create.extend(_make_slots("14:00", 10, 30, 'TARDE'))
                elif shift in ('MT', 'GD'):
                    # 9 pacientes mañana + última hora administrativa + 10 tarde
                    m_slots = _make_slots("07:30", 10, 33, 'MAÑANA')
                    last = m_slots.pop()
                    slots_to_create.extend(m_slots)
                    slots_to_create.append({'inicio': last['inicio'], 'fin': last['fin'], 'turno': 'ADMINISTRATIVA'})
                    slots_to_create.extend(_make_slots("14:00", 10, 30, 'TARDE'))
            elif is_to:
                # TERAPIA OCUPACIONAL: 45 min, M sin hora admin pero con 1 paciente en tarde
                if shift in ('M',):
                    slots_to_create.extend(_make_slots("07:30", 7, 45, 'MAÑANA'))
                    slots_to_create.append({'inicio': '13:50', 'fin': '14:35', 'turno': 'TARDE'})
                elif shift in ('T',):
                    slots_to_create.extend(_make_slots("13:30", 6, 45, 'TARDE'))
                elif shift in ('MT', 'GD'):
                    # 6 pacientes mañana + última hora administrativa + 6 tarde
                    m_slots = _make_slots("07:30", 7, 45, 'MAÑANA')
                    last = m_slots.pop()
                    slots_to_create.extend(m_slots)
                    slots_to_create.append({'inicio': last['inicio'], 'fin': last['fin'], 'turno': 'ADMINISTRATIVA'})
                    slots_to_create.extend(_make_slots("13:45", 6, 45, 'TARDE'))
            elif is_med:
                # MÉDICO/PSIQUIATRA: 40 min por cita
                if shift in ('M',):
                    # Solo mañana: 7 citas + 1 hora administrativa
                    slots_to_create.extend(_make_slots("07:30", 7, 40, 'MAÑANA'))
                    slots_to_create.append({'inicio': '12:10', 'fin': '13:00', 'turno': 'ADMINISTRATIVA'})
                elif shift in ('T',):
                    # Solo tarde: inicia 13:30, 6 citas
                    slots_to_create.extend(_make_slots("13:30", 6, 40, 'TARDE'))
                elif shift in ('MT', 'GD'):
                    # MT y GD: mañana 7 + última hora administrativa + tarde 7
                    m_slots = _make_slots("07:30", 8, 40, 'MAÑANA')
                    last = m_slots.pop()
                    slots_to_create.extend(m_slots)
                    slots_to_create.append({'inicio': last['inicio'], 'fin': last['fin'], 'turno': 'ADMINISTRATIVA'})
                    slots_to_create.extend(_make_slots("14:00", 7, 40, 'TARDE'))
            else:
                # PSICÓLOGO y otros: 45 min por cita
                if shift in ('M',):
                    # Solo mañana: 6 citas + 1 hora administrativa
                    slots_to_create.extend(_make_slots("07:30", 6, 45, 'MAÑANA'))
                    slots_to_create.append({'inicio': '12:00', 'fin': '13:00', 'turno': 'ADMINISTRATIVA'})
                elif shift in ('T',):
                    # Solo tarde: inicia 13:30 para acabar ~18:00, 6 citas
                    slots_to_create.extend(_make_slots("13:30", 6, 45, 'TARDE'))
                elif shift in ('MT', 'GD'):
                    # MT y GD: mañana 6 + última hora administrativa + tarde 6
                    m_slots = _make_slots("07:30", 7, 45, 'MAÑANA')
                    last = m_slots.pop()
                    slots_to_create.extend(m_slots)
                    slots_to_create.append({'inicio': last['inicio'], 'fin': last['fin'], 'turno': 'ADMINISTRATIVA'})
                    slots_to_create.extend(_make_slots("13:45", 6, 45, 'TARDE'))
            prev_appointments = existing.get((prof_data['nombre'], date_str), [])
            prev_by_order = sorted(prev_appointments, key=lambda x: x['hora_inicio'])
            for i, slot in enumerate(slots_to_create):
                pac=''; dni=''; edad=''; cel=''; obs=''; estado='Disponible'; tipo=''; app_act=''; asist='Pendiente'; sihce=0; sihce_pid=0
                if i < len(prev_by_order):
                    prev = prev_by_order[i]; pac=prev['paciente']; dni=prev['dni']; cel=prev['celular']
                    obs=prev['observaciones']; estado=prev['estado']; tipo=prev['tipo_paciente']; asist=prev['asistencia']
                    sihce = prev.get('sihce', 0); sihce_pid = prev.get('sihce_prof_id', 0); edad = prev.get('edad', ''); app_act = prev.get('actividad_app', '')
                conn.execute("INSERT INTO citas (profesional_id,fecha,hora_inicio,hora_fin,turno,area,paciente,dni,edad,celular,observaciones,estado,tipo_paciente,actividad_app,asistencia,sihce,sihce_prof_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (prof_data['id'], date_str, slot['inicio'], slot['fin'], slot['turno'], prof_data['especialidad'], pac, dni, edad, cel, obs, estado, tipo, app_act, asist, sihce, sihce_pid))
                count += 1
    conn.commit()
    return count

def get_default_roster():
    return ""


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
<div class="login-header"><span class="login-icon">🏥</span><h1>Sistema de Citas</h1><p>Centro de Salud Mental Comunitario</p></div>
{error_html}
<form method="POST" class="login-form">
<div class="form-group"><label for="username">Usuario</label><input type="text" id="username" name="username" required autofocus placeholder="Ingrese su usuario" class="form-input"></div>
<div class="form-group"><label for="password">Contraseña</label><div style="position:relative"><input type="password" id="password" name="password" required placeholder="Ingrese su contraseña" class="form-input" style="padding-right:40px"><button type="button" id="toggle-pw" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;font-size:1.1rem">👁️</button></div></div>
<script>document.getElementById("toggle-pw").onclick=function(){{var p=document.getElementById("password");if(p.type=="password"){{p.type="text";this.textContent="🙈"}}else{{p.type="password";this.textContent="👁️"}}}}</script>
<button type="submit" class="btn btn-primary btn-full">Ingresar</button>
</form>
<div class="login-footer"><small>Usuario inicial: <b>admin</b> / Contraseña: <b>admin123</b></small></div>
</div></div></body></html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==============================================================================
# API: FECHAS CON CALENDARIO VISUAL
# ==============================================================================
@app.route('/static/app.js')
def serve_app_js():
    js = """
function onProfChange(v){
    if(!v){document.getElementById("cal-container").innerHTML="";return}
    fetch("/api/fechas/"+v)
        .then(function(r){return r.json()})
        .then(function(d){window._calFechas=d;window._calMonthIdx=null;renderCalendar(d)})
        .catch(function(e){console.error("Error:",e)});
}

function renderCalendar(fechas){
    var c=document.getElementById("cal-container");
    if(!fechas.length){c.innerHTML='<p style="padding:.5rem;color:#6b7280">Sin fechas programadas</p>';return}
    var months={};var monthKeys=[];
    fechas.forEach(function(f){
        var k=f.year+"-"+f.month;
        if(!months[k]){months[k]={year:f.year,month:f.month,dates:{}};monthKeys.push(k)}
        months[k].dates[f.day]={turno:f.turno,value:f.value,lleno:f.lleno||0,ocupados:f.ocupados||0,total:f.total||0};
    });
    monthKeys.sort();
    // Auto-select month based on selected date or current date
    if(window._calMonthIdx===null||window._calMonthIdx===undefined){
        var selDate=document.getElementById("sel-fecha").value;
        var curKey;
        if(selDate){var parts=selDate.split("-");curKey=parseInt(parts[0])+"-"+parseInt(parts[1])}
        else{var now=new Date();curKey=now.getFullYear()+"-"+(now.getMonth()+1)}
        window._calMonthIdx=monthKeys.indexOf(curKey);
        if(window._calMonthIdx<0)window._calMonthIdx=monthKeys.length-1;
    }
    if(window._calMonthIdx<0)window._calMonthIdx=0;
    if(window._calMonthIdx>=monthKeys.length)window._calMonthIdx=monthKeys.length-1;
    window._calMonthKeys=monthKeys;

    var meses=["","Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
    var dias=["L","M","X","J","V","S","D"];
    var html="";
    var selF=document.getElementById("sel-fecha").value;

    // Month navigation
    var mk=monthKeys[window._calMonthIdx];
    var m=months[mk];
    var prevBtn=window._calMonthIdx>0?'<button onclick="calPrevMonth()" style="background:none;border:1px solid #ccc;border-radius:4px;cursor:pointer;padding:2px 8px;font-size:1rem">◀</button>':'<span style="width:30px"></span>';
    var nextBtn=window._calMonthIdx<monthKeys.length-1?'<button onclick="calNextMonth()" style="background:none;border:1px solid #ccc;border-radius:4px;cursor:pointer;padding:2px 8px;font-size:1rem">▶</button>':'<span style="width:30px"></span>';
    html+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">'+prevBtn+'<strong style="font-size:.9rem">'+meses[m.month]+' '+m.year+'</strong>'+nextBtn+'</div>';
    html+='<div class="cal-grid">';
    dias.forEach(function(d){html+='<div class="cal-header">'+d+'</div>'});
    var fd=new Date(m.year,m.month-1,1).getDay();
    fd=fd===0?6:fd-1;
    for(var i=0;i<fd;i++)html+='<div class="cal-day empty"></div>';
    var dm=new Date(m.year,m.month,0).getDate();
    for(var d=1;d<=dm;d++){
        var info=m.dates[d];
        if(info){
            var cls="turno-"+info.turno.toLowerCase();
            var sel=info.value===selF?" selected":"";
            var lleno_s=info.lleno?'border:2px solid #c62828;box-shadow:0 0 4px #c62828':'';
            var badge=info.lleno?'<span style="position:absolute;top:-3px;right:-3px;background:#c62828;color:#fff;border-radius:50%;width:15px;height:15px;font-size:9px;display:flex;align-items:center;justify-content:center;font-weight:bold">!</span>':'<span style="position:absolute;bottom:0;right:1px;font-size:7px;opacity:.6;color:#333">'+info.ocupados+'/'+info.total+'</span>';
            html+='<div class="cal-day '+cls+sel+'" style="position:relative;'+lleno_s+'" onclick="selectDate('+String.fromCharCode(39)+info.value+String.fromCharCode(39)+')" title="'+info.turno+(info.lleno?' - LLENO':' - '+info.ocupados+'/'+info.total)+'">'+d+badge+'</div>';
        }else{
            html+='<div class="cal-day empty" style="color:#ccc;cursor:default">'+d+'</div>';
        }
    }
    html+='</div>';
    html+='<div class="cal-legend"><span><span class="cal-legend-dot" style="background:#1565c0"></span> MT/GD</span><span><span class="cal-legend-dot" style="background:#ff8f00"></span> M</span><span><span class="cal-legend-dot" style="background:#2e7d32"></span> T</span><span><span style="display:inline-block;width:10px;height:10px;border:2px solid #c62828;border-radius:50%;margin-right:3px"></span> Lleno</span><span style="font-size:.7rem;color:#666">N/T = ocupados/total</span></div>';
    c.innerHTML=html;
}
function calPrevMonth(){window._calMonthIdx--;renderCalendar(window._calFechas)}
function calNextMonth(){window._calMonthIdx++;renderCalendar(window._calFechas)}

function selectDate(f){
    var p=document.getElementById("sel-prof").value;
    if(p&&f)window.location.href="/?prof_id="+p+"&fecha="+f;
}

function openModal(id,h){
    document.getElementById("modal-cita-id").value=id;
    document.getElementById("modal-hora").textContent=h;
    document.getElementById("modal-agendar").style.display="flex";
}

function closeModal(){
    document.getElementById("modal-agendar").style.display="none";
}

function marcarAsistencia(id,e,btn){
    var isActive=btn&&(btn.classList.contains("btn-asist-active")||btn.classList.contains("btn-asist-no-active"));
    var current=isActive?"Pendiente":e;
    fetch("/cita/asistencia/"+id+"/"+encodeURIComponent(current),{method:"POST"}).then(function(){location.reload()});
}

function toggleSihce(id,v){
    fetch("/cita/sihce/"+id+"/"+v,{method:"POST"}).then(function(){location.reload()});
}

function toggleSihceProf(v){

function toggleTipoFields(v){
    var appDiv=document.getElementById("app-fields");
    var adminMsg=document.getElementById("admin-msg");
    var pacField=document.getElementById("pac-input");
    var pacReq=document.getElementById("pac-req");
    if(v==="APP"){
        appDiv.style.display="block";
        adminMsg.style.display="none";
        if(pacField){pacField.removeAttribute("required");pacField.placeholder="Opcional para APP";}
        if(pacReq)pacReq.style.display="none";
    }else if(v==="ADMINISTRATIVA"){
        appDiv.style.display="none";
        adminMsg.style.display="block";
        if(pacField){pacField.removeAttribute("required");pacField.placeholder="Opcional";}
        if(pacReq)pacReq.style.display="none";
    }else{
        appDiv.style.display="none";
        adminMsg.style.display="none";
        if(pacField){pacField.setAttribute("required","required");pacField.placeholder="Nombre completo";}
        if(pacReq)pacReq.style.display="inline";
    }
}
function toggleAppManual(v){
    document.getElementById("app-manual").style.display=(v==="OTRO")?"block":"none";
}
    var d=document.getElementById("sihce-prof-div");
    if(v==="1"){
        d.style.display="block";
        fetch("/api/sihce_profs").then(function(r){return r.json()}).then(function(ps){
            var s=document.getElementById("sihce-prof-sel");
            s.innerHTML='<option value="0">-- Seleccionar --</option>';
            ps.forEach(function(p){
                s.innerHTML+='<option value="'+p.id+'">'+p.nombre+' ('+p.esp+')</option>';
            });
        });
    }else{
        d.style.display="none";
    }
}

var modalEl=document.getElementById("modal-agendar");
if(modalEl)modalEl.addEventListener("click",function(e){if(e.target===this)closeModal()});
"""
    resp = make_response(js)
    resp.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp

@app.route('/api/sihce_profs')
@login_required
def api_sihce_profs():
    """Return medical professionals for SIHCE pairing"""
    conn = get_db()
    profs = conn.execute("SELECT id, nombre, especialidad FROM profesionales WHERE activo=1 AND especialidad IN ('MEDICINA','PSIQUIATRÍA') ORDER BY orden").fetchall()
    conn.close()
    return jsonify([{'id': p['id'], 'nombre': p['nombre'], 'especialidad': p['especialidad']} for p in profs])

@app.route('/api/fechas/<int:prof_id>')
@login_required
def api_fechas(prof_id):
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT fecha FROM citas WHERE profesional_id=? ORDER BY fecha", (prof_id,)).fetchall()
    # Get turno info per date from roles_mensuales
    turno_map = {}
    turno_rows = conn.execute("SELECT r.dia, r.turno, r.mes, r.anio FROM roles_mensuales r WHERE r.profesional_id=?", (prof_id,)).fetchall()
    for tr in turno_rows:
        key = f"{tr['anio']}-{tr['mes']:02d}-{tr['dia']:02d}"
        turno_map[key] = tr['turno']
    # Fallback: deduce turno from citas if not in roles_mensuales
    for r in rows:
        if r['fecha'] not in turno_map:
            turnos = conn.execute("SELECT DISTINCT turno FROM citas WHERE profesional_id=? AND fecha=? AND turno!='ADMINISTRATIVA'", (prof_id, r['fecha'])).fetchall()
            t_list = [t['turno'] for t in turnos]
            if 'MAÑANA' in t_list and 'TARDE' in t_list:
                turno_map[r['fecha']] = 'MT'
            elif 'MAÑANA' in t_list:
                turno_map[r['fecha']] = 'M'
            elif 'TARDE' in t_list:
                turno_map[r['fecha']] = 'T'
    fechas = []
    for r in rows:
        turno = turno_map.get(r['fecha'], 'M')
        total = conn.execute("SELECT COUNT(*) as n FROM citas WHERE profesional_id=? AND fecha=? AND turno!='ADMINISTRATIVA'", (prof_id, r['fecha'])).fetchone()['n']
        ocupados = conn.execute("SELECT COUNT(*) as n FROM citas WHERE profesional_id=? AND fecha=? AND estado='Confirmado'", (prof_id, r['fecha'])).fetchone()['n']
        lleno = 1 if (total > 0 and ocupados >= total) else 0
        try:
            dt = datetime.strptime(r['fecha'], '%Y-%m-%d')
            dia_sem = DIAS_CORTO[dt.weekday()]
            fechas.append({'value': r['fecha'], 'label': f"{dt.day} {dia_sem} ({dt.strftime('%d/%m')})", 'turno': turno, 'day': dt.day, 'month': dt.month, 'year': dt.year, 'weekday': dt.weekday(), 'lleno': lleno, 'ocupados': ocupados, 'total': total})
        except:
            fechas.append({'value': r['fecha'], 'label': r['fecha'], 'turno': turno, 'lleno': lleno})
    conn.close()
    return jsonify(fechas)

# ==============================================================================
# AGENDA PRINCIPAL
# ==============================================================================
@app.route('/')
@login_required
def agenda():
    conn = get_db()
    prof_id = request.args.get('prof_id', '')
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    profesionales = conn.execute("SELECT * FROM profesionales WHERE activo=1 ORDER BY CASE especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, orden").fetchall()
    prof_options = '<option value="">— Seleccionar profesional —</option>'
    esp_colors = {'PSIQUIATRÍA':'#e8eaf6','PSIQUIATRÍA - LOCACIÓN':'#b2dfdb','MEDICINA':'#e3f2fd','PSICOLOGÍA':'#fff8e1','TERAPIA DE LENGUAJE':'#e8f5e9','TERAPIA OCUPACIONAL':'#fce4ec','SIHCE':'#f3e5f5'}
    for p in profesionales:
        sel = 'selected' if str(p['id']) == str(prof_id) else ''
        bg = esp_colors.get(p['especialidad'], '#f5f5f5')
        prof_options += f'<option value="{p["id"]}" {sel} style="background:{bg};padding:4px">{p["nombre"]} ({p["especialidad"]})</option>'
    citas_html = ''
    if prof_id and fecha:
        citas = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.color_bg, p.color_font
            FROM citas c JOIN profesionales p ON p.id=c.profesional_id
            WHERE c.profesional_id=? AND c.fecha=? ORDER BY
            CASE c.turno WHEN 'MAÑANA' THEN 1 WHEN 'ADMINISTRATIVA' THEN 2 WHEN 'TARDE' THEN 3 END,
            c.hora_inicio""", (prof_id, fecha)).fetchall()
        if citas:
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_info = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
            except: fecha_info = fecha
            total = len([c for c in citas if c['turno'] != 'ADMINISTRATIVA'])
            ocupados = sum(1 for c in citas if c['estado'] == 'Confirmado')
            pi = citas[0]
            citas_html += f'<div class="date-banner"><span class="prof-chip" style="background:{pi["color_bg"]};color:{pi["color_font"]}">{pi["prof_nombre"]}</span><strong>{fecha_info}</strong><span class="badge badge-info">{total} cupos</span><span class="badge badge-success">{total-ocupados} disponibles</span><span class="badge badge-danger">{ocupados} ocupados</span></div>'
            citas_html += '<div class="table-wrapper"><table class="citas-table"><thead><tr><th>Turno</th><th>Hora</th><th>Paciente</th><th>DNI</th><th>Tipo</th><th>SIHCE</th><th>Estado</th><th>Asistencia</th><th>Acciones</th></tr></thead><tbody>'
            ct = ''
            for c in citas:
                # La hora administrativa pertenece visualmente a la mañana
                turno_grupo = 'MAÑANA' if c['turno'] == 'ADMINISTRATIVA' else c['turno']
                if turno_grupo != ct:
                    ct = turno_grupo
                    icon = '☀️' if ct == 'MAÑANA' else ('🌙' if ct == 'TARDE' else '📋')
                    citas_html += f'<tr class="turno-divider"><td colspan="9"><span class="turno-label">{icon} {ct}</span></td></tr>'
                if c['turno'] == 'ADMINISTRATIVA':
                    citas_html += f'<tr class="cita-row" style="background:#fff3e0;border-left:4px solid #ff9800"><td>ADM</td><td class="td-hora"><strong>{c["hora_inicio"]} - {c["hora_fin"]}</strong></td><td colspan="7"><em style="color:#e65100">📋 Hora Administrativa</em></td></tr>'
                    continue
                tp = c['tipo_paciente'] if c['tipo_paciente'] else ''
                rc = 'row-app' if tp in ('APP','ADMINISTRATIVA') and c['estado'] == 'Confirmado' else ('row-ocupado' if c['estado'] == 'Confirmado' else 'row-disponible')
                st = f'border-left:4px solid {c["color_bg"]};' if c['estado'] == 'Confirmado' else ''
                if c['estado'] == 'Confirmado':
                    pc = f'<span class="paciente-nombre">{c["paciente"]}</span>'
                    if c['edad']: pc += f' <small>({c["edad"]} años)</small>'
                    if c['celular']: pc += f'<br><small class="text-muted">📱 {c["celular"]}</small>'
                    if c['actividad_app']: pc += f'<br><small style="color:#e65100;font-weight:600">🏷️ APP: {c["actividad_app"]}</small>'
                    if c['observaciones']: pc += f'<br><small class="text-muted">📝 {c["observaciones"]}</small>'
                else: pc = '<span class="text-available">Disponible</span>'
                th = ''
                if c['tipo_paciente']:
                    bc = 'badge-new' if c['tipo_paciente'] == 'NUEVO' else 'badge-cont'
                    th = f'<span class="badge {bc}">{c["tipo_paciente"]}</span>'
                sh = ''
                if c['estado'] == 'Confirmado':
                    sv = c['sihce'] if c['sihce'] else 0
                    if sv:
                        sh = '<span class="sihce-tag">SIHCE</span>'
                        sp_id = c.get('sihce_prof_id', 0) or 0
                        if sp_id:
                            sp = conn.execute("SELECT nombre FROM profesionales WHERE id=?", (sp_id,)).fetchone()
                            if sp: sh += f'<br><small style="color:#e65100">🔗 {sp["nombre"]}</small>'
                    sh += f' <span class="btn-asist" style="opacity:0.4;cursor:default" title="SIHCE deshabilitado">🔗</span>'
                sc = 'status-confirmado' if c['estado'] == 'Confirmado' else 'status-disponible'
                sthtml = f'<span class="status-dot {sc}"></span>{c["estado"]}'
                ah = ''
                if c['estado'] == 'Confirmado':
                    aa = 'btn-asist-active' if c['asistencia'] == 'Asistió' else ''
                    na = 'btn-asist-no-active' if c['asistencia'] == 'No asistió' else ''
                    pend = 'pendiente' if c['asistencia'] not in ('Asistió', 'No asistió') and c['tipo_paciente'] not in ('APP', 'ADMINISTRATIVA') else ''
                    ah = f'<div class="asistencia-btns {pend}"><button class="btn-asist {aa}" onclick="marcarAsistencia({c["id"]},\'Asistió\',this)" title="Asistió (clic para desmarcar)">✅</button><button class="btn-asist {na}" onclick="marcarAsistencia({c["id"]},\'No asistió\',this)" title="No asistió (clic para desmarcar)">❌</button></div>'
                if c['estado'] == 'Disponible':
                    he = c["hora_inicio"] + " - " + c["hora_fin"]
                    act = f'<button class="btn btn-sm btn-success" onclick="openModal({c["id"]},\'{he}\')">➕ Agendar</button>'
                else:
                    pe = c["paciente"].replace("'","\\'")
                    act = f'<a href="/cita/editar/{c["id"]}" class="btn btn-sm btn-warning" title="Editar">✏️</a> <a href="/cita/migrar/{c["id"]}" class="btn btn-sm btn-primary" title="Migrar">📦</a> <a href="/cita/imprimir/{c["id"]}" target="_blank" class="btn btn-sm btn-secondary" title="Imprimir">🖨️</a> <form method="POST" action="/cita/eliminar/{c["id"]}" style="display:inline" onsubmit="return confirm(\'¿Eliminar cita de {pe}?\')"><button type="submit" class="btn btn-sm btn-danger">🗑️</button></form>'
                citas_html += f'<tr class="cita-row {rc}" style="{st}"><td>{c["turno"][:3]}</td><td class="td-hora"><strong>{c["hora_inicio"]} - {c["hora_fin"]}</strong></td><td>{pc}</td><td>{c["dni"] if c["estado"]=="Confirmado" else ""}</td><td>{th}</td><td>{sh}</td><td>{sthtml}</td><td>{ah}</td><td>{act}</td></tr>'
            citas_html += '</tbody></table></div>'
        else: citas_html = '<div class="empty-state"><p>No hay cupos para esta combinación.</p></div>'
    elif not prof_id:
        citas_html = '<div class="empty-state"><div class="empty-icon">📋</div><h3>Seleccione un profesional para ver su agenda</h3><p>Use los filtros de arriba para comenzar</p></div>'
    is_lector = session.get('user_rol') == 'lector'
    conn.close()
    CALENDAR_JS = '<script src="/static/app.js"></script>'
    init_js = f'<script>onProfChange("{prof_id}");</script>' if prof_id else ''
    modal_html = '''<div id="modal-agendar" class="modal" style="display:none"><div class="modal-content">
        <div class="modal-header"><h3>➕ Agendar Cita</h3><button class="modal-close" onclick="closeModal()">×</button></div>
        <form method="POST" action="/cita/agendar"><input type="hidden" name="cita_id" id="modal-cita-id">
        <div class="modal-body"><p id="modal-hora" class="modal-hora-display"></p>
        <div class="form-group"><label>Paciente <span id="pac-req">*</span></label><input type="text" name="paciente" id="pac-input" class="form-input" placeholder="Nombre completo"></div>
        <div class="form-row"><div class="form-group"><label>DNI</label><input type="text" name="dni" class="form-input" maxlength="8" placeholder="12345678"></div>
        <div class="form-group"><label>Edad</label><input type="text" name="edad" class="form-input" maxlength="3" placeholder="25"></div>
        <div class="form-group"><label>Celular</label><input type="text" name="celular" class="form-input" maxlength="9" placeholder="987654321"></div></div>
        <div class="form-row"><div class="form-group"><label>Tipo</label><select name="tipo_paciente" id="tipo-sel" class="form-select" onchange="toggleTipoFields(this.value)"><option value="NUEVO">NUEVO</option><option value="CONTINUADOR">CONTINUADOR</option><option value="APP">APP (Actividad Preventiva)</option><option value="ADMINISTRATIVA">HORA ADMINISTRATIVA</option></select></div>
        </div>
        <input type="hidden" name="sihce" value="0"><input type="hidden" name="sihce_prof_id" value="0">
        <div id="app-fields" style="display:none;background:#e8f5e9;padding:.75rem;border-radius:6px;border:2px solid #4caf50;margin-bottom:.5rem">
        <div class="form-group"><label style="color:#2e7d32">Tipo de Actividad APP</label><select name="actividad_app" id="app-sel" class="form-select" onchange="toggleAppManual(this.value)">
        <option value="">— Seleccionar —</option><option value="VISITA DOMICILIARIA">Visita domiciliaria</option><option value="SEGUIMIENTO A USUARIOS">Seguimiento a usuarios</option>
        <option value="GAM ADULTO">GAM adulto</option><option value="GAM NIÑO">GAM niño</option><option value="GAM ADICCIONES">GAM adicciones</option>
        <option value="CHARLA RADIAL">Charla radial</option><option value="CHARLA EN COMUNIDAD">Charla en comunidad</option>
        <option value="HOGAR PROTEGIDO">Hogar protegido</option>
        <option value="REALIZACIÓN DE INFORMES">Realización de Informes</option><option value="REUNIÓN DE PERSONAL">Reunión de personal</option>
        <option value="REUNIÓN PROTOCOLO ACTUACIÓN CONJUNTA">Reunión Protocolo de Actuación Conjunta</option>
        <option value="REUNIÓN ASOCIACIÓN FAMILIARES">Reunión de la asociación de familiares</option>
        <option value="REUNIÓN TÉCNICA COMITÉ SALUD MENTAL">Reunión Técnica Comité de Salud Mental</option>
        <option value="OTRO">✏️ Otro (escribir manualmente)</option></select></div>
        <div id="app-manual" class="form-group" style="display:none"><label style="color:#2e7d32">Describir actividad</label><input type="text" name="actividad_app_manual" class="form-input" placeholder="Escriba la actividad..."></div>
        </div>
        <div id="admin-msg" style="display:none;background:#fff3e0;padding:.75rem;border-radius:6px;border:2px solid #ff9800;margin-bottom:.5rem;color:#e65100;font-weight:600">📋 Se registrará como HORA ADMINISTRATIVA</div>
        <div class="form-group"><label>Observaciones</label><input type="text" name="observaciones" class="form-input" placeholder="Opcional"></div></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
        <button type="submit" class="btn btn-success">💾 Agendar</button></div></form></div></div>'''
    content = f'''<div class="page-header"><h2>📅 Agenda de Citas</h2></div>
    <div class="card" style="padding:1rem"><div class="filter-row">
        <div class="filter-group"><label>Profesional</label><select id="sel-prof" class="form-select" onchange="onProfChange(this.value)">{prof_options}</select></div>
        <div class="filter-group"><label>Fecha</label><div id="cal-container"></div><input type="hidden" id="sel-fecha" value="{fecha}"></div>
    </div></div>{citas_html}{modal_html}''' + CALENDAR_JS + init_js
    flash_msgs = session.pop('_flashes', [])
    return page('Agenda - Sistema de Citas', content, flash_msgs, show_asist_banner=True)


    flash_msgs = session.pop('_flashes', [])
    return page('Agenda - Sistema de Citas', content, flash_msgs)

# ==============================================================================
# CITAS: AGENDAR, ELIMINAR, ASISTENCIA, SIHCE
# ==============================================================================
@app.route('/cita/agendar', methods=['POST'])
@login_required
def agendar_cita():
    if session.get('user_rol')=='lector':
        flash('No tiene permisos (solo lectura)','danger')
        return redirect(request.referrer or '/')
    cita_id = request.form.get('cita_id')
    paciente = request.form.get('paciente', '').strip().upper()
    dni = request.form.get('dni', '').strip()
    edad = request.form.get('edad', '').strip()
    celular = request.form.get('celular', '').strip()
    obs = request.form.get('observaciones', '').strip()
    tipo = request.form.get('tipo_paciente', 'NUEVO')
    sihce = int(request.form.get('sihce', 0))
    sihce_prof_id = int(request.form.get('sihce_prof_id', 0))
    actividad_app = request.form.get('actividad_app', '').strip()
    # Handle APP manual input
    if actividad_app == 'OTRO':
        actividad_app = request.form.get('actividad_app_manual', '').strip().upper()
    # Handle ADMINISTRATIVA type
    if tipo == 'ADMINISTRATIVA':
        paciente = paciente or 'HORA ADMINISTRATIVA'
        actividad_app = ''
    elif tipo == 'APP':
        paciente = paciente or actividad_app or 'ACTIVIDAD APP'
    elif not paciente:
        flash('El nombre del paciente es obligatorio', 'danger')
        return redirect(request.referrer or '/')
    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if not cita or cita['estado'] != 'Disponible':
        flash('Cupo no disponible', 'warning')
        conn.close()
        return redirect(request.referrer or '/')
    conn.execute("UPDATE citas SET paciente=?, dni=?, edad=?, celular=?, observaciones=?, estado='Confirmado', tipo_paciente=?, sihce=?, sihce_prof_id=?, actividad_app=?, creado_por=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?",
        (paciente, dni, edad, celular, obs, tipo, sihce, sihce_prof_id, actividad_app, session['user_id'], session['user_id'], cita_id))
    accion = 'APP' if tipo == 'APP' else ('ADMINISTRATIVA' if tipo == 'ADMINISTRATIVA' else 'AGENDAR')
    conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], accion, f'{tipo}: {paciente} | {actividad_app}' if tipo in ('APP','ADMINISTRATIVA') else f'Paciente: {paciente} | DNI: {dni}'))
    conn.commit(); conn.close()
    flash(f'{"Actividad APP" if tipo=="APP" else ("Hora administrativa" if tipo=="ADMINISTRATIVA" else "Cita")} registrada: {paciente}', 'success')
    return redirect(request.referrer or '/')

@app.route('/cita/eliminar/<int:cita_id>', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    if session.get('user_rol')=='lector':
        flash('No tiene permisos (solo lectura)','danger')
        return redirect(request.referrer or '/')
    conn = get_db()
    cita = conn.execute("SELECT * FROM citas WHERE id=?", (cita_id,)).fetchone()
    if cita and cita['estado'] != 'Disponible':
        conn.execute("UPDATE citas SET paciente='',dni='',edad='',celular='',observaciones='',estado='Disponible',tipo_paciente='',actividad_app='',asistencia='Pendiente',sihce=0,sihce_prof_id=0,modificado_por=?,modificado_en=CURRENT_TIMESTAMP WHERE id=?",
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
    if session.get('user_rol')=='lector': return jsonify({'error':'Sin permisos'}),403
    if estado not in ('Asistió', 'No asistió', 'Pendiente'): abort(400)
    conn = get_db()
    conn.execute("UPDATE citas SET asistencia=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?", (estado, session['user_id'], cita_id))
    conn.execute("INSERT INTO historial (cita_id,usuario_id,accion,detalle) VALUES (?,?,?,?)",
        (cita_id, session['user_id'], 'ASISTENCIA', f'Marcado como: {estado}'))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/cita/sihce/<int:cita_id>/<int:val>', methods=['POST'])
@login_required
def toggle_sihce(cita_id, val):
    if session.get('user_rol')=='lector': return jsonify({'error':'Sin permisos'}),403
    conn = get_db()
    conn.execute("UPDATE citas SET sihce=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?", (val, session['user_id'], cita_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ==============================================================================
# REPORTE DIARIO - Pacientes programados por día
# ==============================================================================
@app.route('/unir_turnos', methods=['GET', 'POST'])
@admin_required
def unir_turnos():
    conn = get_db()
    profesionales = conn.execute("""SELECT * FROM profesionales WHERE activo=1 
        ORDER BY CASE especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, orden""").fetchall()
    resultado = ''

    if request.method == 'POST':
        prof_id = int(request.form.get('prof_id', 0))
        fecha_m = request.form.get('fecha_m', '')
        fecha_t = request.form.get('fecha_t', '')
        fecha_destino = request.form.get('fecha_destino', '')
        cual_m = request.form.get('cual_m', 'fecha_m')  # which date provides MAÑANA
        confirmar = request.form.get('confirmar', '')

        if not prof_id or not fecha_m or not fecha_t:
            flash('Complete todos los campos', 'danger')
            conn.close()
            return redirect('/unir_turnos')

        prof = conn.execute("SELECT * FROM profesionales WHERE id=?", (prof_id,)).fetchone()
        if not prof:
            flash('Profesional no encontrado', 'danger')
            conn.close()
            return redirect('/unir_turnos')

        if not fecha_destino:
            fecha_destino = fecha_m if cual_m == 'fecha_m' else fecha_t

        # Get ALL slots from source dates (including empty ones, respecting position)
        src_m = fecha_m if cual_m == 'fecha_m' else fecha_t
        src_t = fecha_t if cual_m == 'fecha_m' else fecha_m

        # Get all slots that are not ADMINISTRATIVA, in order
        all_slots_m = [dict(c) for c in conn.execute(
            "SELECT * FROM citas WHERE profesional_id=? AND fecha=? AND turno!='ADMINISTRATIVA' ORDER BY hora_inicio",
            (prof_id, src_m)).fetchall()]
        all_slots_t = [dict(c) for c in conn.execute(
            "SELECT * FROM citas WHERE profesional_id=? AND fecha=? AND turno!='ADMINISTRATIVA' ORDER BY hora_inicio",
            (prof_id, src_t)).fetchall()]

        # Generate MT slots for destination
        is_med = prof['especialidad'] in ('MEDICINA', 'PSIQUIATRÍA', 'SIHCE')
        is_to = prof['especialidad'] == 'TERAPIA OCUPACIONAL'
        is_loc = prof['especialidad'] == 'PSIQUIATRÍA - LOCACIÓN'
        if is_loc:
            new_m = _make_slots("07:30", 10, 33, 'MAÑANA')
            new_t = _make_slots("14:00", 10, 30, 'TARDE')
        elif is_to:
            new_m = _make_slots("07:30", 7, 45, 'MAÑANA')
            new_t = _make_slots("13:45", 6, 45, 'TARDE')
        elif is_med:
            new_m = _make_slots("07:30", 8, 40, 'MAÑANA')
            new_t = _make_slots("14:00", 7, 40, 'TARDE')
        else:
            new_m = _make_slots("07:30", 7, 45, 'MAÑANA')
            new_t = _make_slots("13:45", 6, 45, 'TARDE')

        # Map source slots to new slots position by position (respecting gaps)
        overflow_m = all_slots_m[len(new_m):] if len(all_slots_m) > len(new_m) else []
        overflow_t = all_slots_t[len(new_t):] if len(all_slots_t) > len(new_t) else []
        slots_for_m = all_slots_m[:len(new_m)]
        slots_for_t = all_slots_t[:len(new_t)]

        # Count actual patients (for preview)
        pac_manana = [s for s in slots_for_m if s['estado'] == 'Confirmado']
        pac_tarde = [s for s in slots_for_t if s['estado'] == 'Confirmado']

        if not confirmar:
            try:
                dt_m = datetime.strptime(src_m, '%Y-%m-%d')
                dt_t = datetime.strptime(src_t, '%Y-%m-%d')
                dt_d = datetime.strptime(fecha_destino, '%Y-%m-%d')
                fm = f"{DIAS_ES[dt_m.weekday()]} {dt_m.day} de {MESES_ES[dt_m.month]}"
                ft = f"{DIAS_ES[dt_t.weekday()]} {dt_t.day} de {MESES_ES[dt_t.month]}"
                fd = f"{DIAS_ES[dt_d.weekday()]} {dt_d.day} de {MESES_ES[dt_d.month]}"
            except:
                fm = src_m; ft = src_t; fd = fecha_destino

            preview_m = ''.join(f'<tr><td>{p["paciente"]}</td><td>{p["hora_inicio"]}</td></tr>' for p in pac_manana)
            preview_t = ''.join(f'<tr><td>{p["paciente"]}</td><td>{p["hora_inicio"]}</td></tr>' for p in pac_tarde)
            warning = ''
            if overflow_m or overflow_t:
                warning = f'<div class="flash flash-danger">⚠️ {len(overflow_m)+len(overflow_t)} paciente(s) no caben en el turno MT</div>'

            resultado = f'''<div class="card" style="border:2px solid #1565c0">
                <h3>📋 Vista previa de unión</h3>
                <p><strong>Profesional:</strong> {prof["nombre"]}</p>
                <p><strong>MAÑANA desde:</strong> {fm} ({len(pac_manana)} pacientes → {len(new_m)} cupos)</p>
                <p><strong>TARDE desde:</strong> {ft} ({len(pac_tarde)} pacientes → {len(new_t)} cupos)</p>
                <p><strong>Fecha destino:</strong> {fd} (turno MT)</p>
                {warning}
                <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:.5rem">
                    <div style="flex:1;min-width:200px"><h4>☀️ Mañana ({len(pac_manana)})</h4>
                        <table class="citas-table"><tbody>{preview_m or '<tr><td>Sin pacientes</td></tr>'}</tbody></table></div>
                    <div style="flex:1;min-width:200px"><h4>🌙 Tarde ({len(pac_tarde)})</h4>
                        <table class="citas-table"><tbody>{preview_t or '<tr><td>Sin pacientes</td></tr>'}</tbody></table></div>
                </div>
                <form method="POST" style="margin-top:1rem">
                    <input type="hidden" name="prof_id" value="{prof_id}">
                    <input type="hidden" name="fecha_m" value="{fecha_m}">
                    <input type="hidden" name="fecha_t" value="{fecha_t}">
                    <input type="hidden" name="fecha_destino" value="{fecha_destino}">
                    <input type="hidden" name="cual_m" value="{cual_m}">
                    <input type="hidden" name="confirmar" value="1">
                    <button type="submit" class="btn btn-success btn-lg" onclick="return confirm('¿Confirmar unión de turnos?')">✅ Confirmar Unión</button>
                    <a href="/unir_turnos" class="btn btn-secondary btn-lg">❌ Cancelar</a>
                </form></div>'''
        else:
            # Execute: delete both source dates and create MT at destination
            fechas_a_borrar = set([fecha_m, fecha_t, fecha_destino])
            for f in fechas_a_borrar:
                conn.execute("DELETE FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, f))
                try:
                    dt = datetime.strptime(f, '%Y-%m-%d')
                    conn.execute("DELETE FROM roles_mensuales WHERE profesional_id=? AND anio=? AND mes=? AND dia=?",
                        (prof_id, dt.year, dt.month, dt.day))
                except: pass

            # Update role for destination
            try:
                dt_d = datetime.strptime(fecha_destino, '%Y-%m-%d')
                conn.execute("INSERT OR REPLACE INTO roles_mensuales (profesional_id, anio, mes, dia, turno) VALUES (?,?,?,?,?)",
                    (prof_id, dt_d.year, dt_d.month, dt_d.day, 'MT'))
            except: pass

            # Insert slots: position by position from source to destination
            all_new = new_m + new_t
            idx_m = 0; idx_t = 0
            for slot in all_new:
                pac=''; dni=''; edad=''; cel=''; obs=''; estado='Disponible'
                tipo=''; app_act=''; asist='Pendiente'; sihce=0; sihce_pid=0; creado=None; modif=None

                src = None
                if slot['turno'] == 'MAÑANA' and idx_m < len(slots_for_m):
                    src = slots_for_m[idx_m]; idx_m += 1
                elif slot['turno'] == 'TARDE' and idx_t < len(slots_for_t):
                    src = slots_for_t[idx_t]; idx_t += 1

                if src and src['estado'] == 'Confirmado':
                    pac=src['paciente']; dni=src['dni']; edad=src.get('edad','')
                    cel=src['celular']; obs=src.get('observaciones',''); estado='Confirmado'
                    tipo=src.get('tipo_paciente',''); app_act=src.get('actividad_app','')
                    asist=src.get('asistencia','Pendiente'); sihce=src.get('sihce',0)
                    sihce_pid=src.get('sihce_prof_id',0); creado=src.get('creado_por'); modif=src.get('modificado_por')

                conn.execute("""INSERT INTO citas (profesional_id,fecha,hora_inicio,hora_fin,turno,area,
                    paciente,dni,edad,celular,observaciones,estado,tipo_paciente,actividad_app,
                    asistencia,sihce,sihce_prof_id,creado_por,modificado_por,modificado_en)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (prof_id, fecha_destino, slot['inicio'], slot['fin'], slot['turno'], prof['especialidad'],
                     pac, dni, edad, cel, obs, estado, tipo, app_act, asist, sihce, sihce_pid, creado, modif))

            conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
                (0, session['user_id'], 'UNIR_TURNOS', f'{prof["nombre"]} | M:{src_m} + T:{src_t} → MT:{fecha_destino} | {len(pac_manana)}M+{len(pac_tarde)}T'))
            conn.commit()
            flash(f'Turnos unidos: {prof["nombre"]} → MT en {fecha_destino}. {len(pac_manana)} mañana + {len(pac_tarde)} tarde trasladados.', 'success')
            conn.close()
            return redirect('/unir_turnos')

    conn.close()
    prof_opts = ''.join(f'<option value="{p["id"]}">{p["nombre"]} ({p["especialidad"]})</option>' for p in profesionales)
    content = f'''<div class="page-header"><h2>🔗 Unir Turnos</h2></div>
    <div class="card"><h3>Combinar turno M + turno T en un solo día MT</h3>
    <form method="POST">
        <div class="form-row">
            <div class="form-group"><label>Profesional</label>
                <select name="prof_id" class="form-select" required><option value="">— Seleccionar —</option>{prof_opts}</select>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group"><label>Fecha del turno 1</label>
                <input type="date" name="fecha_m" class="form-input" required>
            </div>
            <div class="form-group"><label>Fecha del turno 2</label>
                <input type="date" name="fecha_t" class="form-input" required>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group"><label>¿Cuál será MAÑANA?</label>
                <select name="cual_m" class="form-select">
                    <option value="fecha_m">Turno 1 = Mañana</option>
                    <option value="fecha_t">Turno 2 = Mañana</option>
                </select>
            </div>
            <div class="form-group"><label>Fecha destino (donde se unen)</label>
                <input type="date" name="fecha_destino" class="form-input" placeholder="Dejar vacío = fecha del turno mañana">
            </div>
        </div>
        <button type="submit" class="btn btn-primary btn-lg">🔍 Ver Vista Previa</button>
    </form></div>
    {resultado}'''
    flash_msgs = session.pop('_flashes', [])
    return page('Unir Turnos - Sistema de Citas', content, flash_msgs)

@app.route('/cambiar_turno', methods=['GET', 'POST'])
@admin_required
def cambiar_turno():
    conn = get_db()
    profesionales = conn.execute("SELECT id, nombre, especialidad FROM profesionales WHERE activo=1 ORDER BY CASE especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, orden").fetchall()

    resultado = ''
    if request.method == 'POST':
        accion = request.form.get('accion', 'cambiar')
        prof_id = int(request.form.get('prof_id', 0))
        fecha = request.form.get('fecha', '')
        nuevo_turno = request.form.get('nuevo_turno', '')
        fecha_destino = request.form.get('fecha_destino', '') or fecha

        # ACCION: ELIMINAR cupos de una fecha
        if accion == 'eliminar':
            if prof_id and fecha:
                confirmar = request.form.get('confirmar', '')
                prof = conn.execute("SELECT * FROM profesionales WHERE id=?", (prof_id,)).fetchone()
                citas_dia = conn.execute("SELECT * FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, fecha)).fetchall()
                pac_conf = [c for c in citas_dia if c['estado'] == 'Confirmado']

                if not confirmar:
                    try:
                        dt = datetime.strptime(fecha, '%Y-%m-%d')
                        fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
                    except: fecha_display = fecha

                    warning = ''
                    if pac_conf:
                        warning = f'<div class="flash flash-danger">⚠️ HAY {len(pac_conf)} PACIENTE(S) AGENDADO(S) que se perderán:<br>'
                        for p in pac_conf: warning += f'• {p["paciente"]} ({p["hora_inicio"]}-{p["hora_fin"]})<br>'
                        warning += '</div>'

                    resultado = f'''<div class="card" style="border:2px solid #c62828">
                        <h3>🗑️ Eliminar cupos</h3>
                        <p><strong>Profesional:</strong> {prof["nombre"]}</p>
                        <p><strong>Fecha:</strong> {fecha_display}</p>
                        <p><strong>Cupos a eliminar:</strong> {len(citas_dia)}</p>
                        {warning}
                        <form method="POST" style="margin-top:1rem">
                            <input type="hidden" name="accion" value="eliminar">
                            <input type="hidden" name="prof_id" value="{prof_id}">
                            <input type="hidden" name="fecha" value="{fecha}">
                            <input type="hidden" name="confirmar" value="1">
                            <button type="submit" class="btn btn-danger btn-lg" onclick="return confirm('¿ELIMINAR todos los cupos de {prof['nombre']} el {fecha}?')">🗑️ Confirmar Eliminación</button>
                            <a href="/cambiar_turno" class="btn btn-secondary btn-lg">❌ Cancelar</a>
                        </form></div>'''
                else:
                    conn.execute("DELETE FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, fecha))
                    try:
                        dt = datetime.strptime(fecha, '%Y-%m-%d')
                        conn.execute("DELETE FROM roles_mensuales WHERE profesional_id=? AND anio=? AND mes=? AND dia=?",
                            (prof_id, dt.year, dt.month, dt.day))
                    except: pass
                    pac_nombres = ', '.join(p['paciente'] for p in pac_conf) if pac_conf else 'ninguno'
                    conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
                        (0, session['user_id'], 'ELIMINAR_CUPOS', f'{prof["nombre"]} | {fecha} | {len(citas_dia)} cupos eliminados | Pacientes: {pac_nombres}'))
                    conn.commit()
                    flash(f'Cupos eliminados: {prof["nombre"]} el {fecha} ({len(citas_dia)} cupos, {len(pac_conf)} pacientes)', 'success')
                    conn.close()
                    return redirect('/cambiar_turno')

            conn.close()
            prof_options = ''.join(f'<option value="{p["id"]}">{p["nombre"]} ({p["especialidad"]})</option>' for p in profesionales)
            flash_msgs = session.pop('_flashes', [])
            return page('Cambiar Turno', _cambiar_turno_form(prof_options, resultado), flash_msgs)

        # ACCION: CAMBIAR turno
        if not prof_id or not fecha or not nuevo_turno:
            flash('Complete todos los campos', 'danger')
            conn.close()
            return redirect('/cambiar_turno')

        prof = conn.execute("SELECT * FROM profesionales WHERE id=?", (prof_id,)).fetchone()
        if not prof:
            flash('Profesional no encontrado', 'danger')
            conn.close()
            return redirect('/cambiar_turno')

        # Get existing appointments from SOURCE date
        citas_existentes = conn.execute(
            "SELECT * FROM citas WHERE profesional_id=? AND fecha=? ORDER BY hora_inicio",
            (prof_id, fecha)).fetchall()
        pacientes = [dict(c) for c in citas_existentes if c['estado'] == 'Confirmado']
        total_prev = len(citas_existentes)

        # Check if DESTINATION date already has slots
        if fecha_destino != fecha:
            citas_destino = conn.execute("SELECT * FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, fecha_destino)).fetchall()
            pac_destino = [c for c in citas_destino if c['estado'] == 'Confirmado']
            if pac_destino:
                flash(f'La fecha destino {fecha_destino} ya tiene {len(pac_destino)} pacientes agendados. Elimine esos cupos primero o elija otra fecha.', 'danger')
                conn.close()
                return redirect('/cambiar_turno')

        # Generate new slots
        is_med = prof['especialidad'] in ('MEDICINA', 'PSIQUIATRÍA', 'SIHCE')
        is_to = prof['especialidad'] == 'TERAPIA OCUPACIONAL'
        is_loc = prof['especialidad'] == 'PSIQUIATRÍA - LOCACIÓN'
        new_slots = []
        if is_loc:
            if nuevo_turno == 'M':
                new_slots = _make_slots("07:30", 10, 33, 'MAÑANA')
            elif nuevo_turno == 'T':
                new_slots = _make_slots("14:00", 10, 30, 'TARDE')
            elif nuevo_turno in ('MT', 'GD'):
                new_slots = _make_slots("07:30", 10, 33, 'MAÑANA')
                new_slots.extend(_make_slots("14:00", 10, 30, 'TARDE'))
        elif is_to:
            if nuevo_turno == 'M':
                new_slots = _make_slots("07:30", 7, 45, 'MAÑANA')
                new_slots.append({'inicio': '13:50', 'fin': '14:35', 'turno': 'TARDE'})
            elif nuevo_turno == 'T':
                new_slots = _make_slots("13:30", 6, 45, 'TARDE')
            elif nuevo_turno in ('MT', 'GD'):
                new_slots = _make_slots("07:30", 7, 45, 'MAÑANA')
                new_slots.extend(_make_slots("13:45", 6, 45, 'TARDE'))
        elif is_med:
            if nuevo_turno == 'M':
                new_slots = _make_slots("07:30", 7, 40, 'MAÑANA')
                new_slots.append({'inicio': '12:10', 'fin': '13:00', 'turno': 'ADMINISTRATIVA'})
            elif nuevo_turno == 'T':
                new_slots = _make_slots("13:30", 6, 40, 'TARDE')
            elif nuevo_turno in ('MT', 'GD'):
                new_slots = _make_slots("07:30", 8, 40, 'MAÑANA')
                new_slots.extend(_make_slots("14:00", 7, 40, 'TARDE'))
        else:
            if nuevo_turno == 'M':
                new_slots = _make_slots("07:30", 6, 45, 'MAÑANA')
                new_slots.append({'inicio': '12:00', 'fin': '13:00', 'turno': 'ADMINISTRATIVA'})
            elif nuevo_turno == 'T':
                new_slots = _make_slots("13:30", 6, 45, 'TARDE')
            elif nuevo_turno in ('MT', 'GD'):
                new_slots = _make_slots("07:30", 7, 45, 'MAÑANA')
                new_slots.extend(_make_slots("13:45", 6, 45, 'TARDE'))

        patient_slots = [s for s in new_slots if s['turno'] != 'ADMINISTRATIVA']
        slots_disponibles = len(patient_slots)
        pacientes_sin_cupo = []
        if len(pacientes) > slots_disponibles:
            pacientes_sin_cupo = pacientes[slots_disponibles:]
            pacientes = pacientes[:slots_disponibles]

        confirmar = request.form.get('confirmar', '')
        if not confirmar:
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
                dt2 = datetime.strptime(fecha_destino, '%Y-%m-%d')
                fecha_dest_display = f"{DIAS_ES[dt2.weekday()]} {dt2.day} de {MESES_ES[dt2.month]} {dt2.year}"
            except:
                fecha_display = fecha; fecha_dest_display = fecha_destino

            turnos_prev = set(c['turno'] for c in citas_existentes if c['turno'] != 'ADMINISTRATIVA')
            turno_prev = ', '.join(turnos_prev) if turnos_prev else 'Sin turno'

            cambio_dia = fecha != fecha_destino
            pac_rows = ''
            for i, p in enumerate(pacientes):
                dest = patient_slots[i]
                pac_rows += f'<tr><td>{p["paciente"]}</td><td>{p["hora_inicio"]}-{p["hora_fin"]}</td><td style="color:green;font-weight:700">{dest["inicio"]}-{dest["fin"]} ({dest["turno"]})</td></tr>'

            warning = ''
            if pacientes_sin_cupo:
                warning = f'<div class="flash flash-danger" style="margin:1rem 0">⚠️ <strong>{len(pacientes_sin_cupo)} paciente(s) NO CABEN</strong> en el nuevo turno:<br>'
                for p in pacientes_sin_cupo:
                    warning += f'• {p["paciente"]} ({p["hora_inicio"]}-{p["hora_fin"]})<br>'
                warning += 'Estos pacientes se perderán si continúa.</div>'

            dia_info = f'<p style="color:#1565c0;font-weight:700">📅 Los pacientes se MOVERÁN al {fecha_dest_display}</p>' if cambio_dia else ''

            resultado = f'''<div class="card" style="border:2px solid #ff8f00">
                <h3>📋 Vista previa del cambio</h3>
                <p><strong>Profesional:</strong> {prof["nombre"]}</p>
                <p><strong>Fecha origen:</strong> {fecha_display} — Turno: {turno_prev} ({total_prev} cupos)</p>
                <p><strong>{"Fecha destino" if cambio_dia else "Misma fecha"}:</strong> {fecha_dest_display if cambio_dia else fecha_display} — Nuevo turno: {nuevo_turno} ({len(new_slots)} cupos, {slots_disponibles} para pacientes)</p>
                <p><strong>Pacientes agendados:</strong> {len(pacientes) + len(pacientes_sin_cupo)}</p>
                {dia_info}{warning}
                {"<div class='table-wrapper'><table class='citas-table'><thead><tr><th>Paciente</th><th>Horario actual</th><th>Nuevo horario</th></tr></thead><tbody>" + pac_rows + "</tbody></table></div>" if pac_rows else "<p>No hay pacientes agendados.</p>"}
                <form method="POST" style="margin-top:1rem">
                    <input type="hidden" name="accion" value="cambiar">
                    <input type="hidden" name="prof_id" value="{prof_id}">
                    <input type="hidden" name="fecha" value="{fecha}">
                    <input type="hidden" name="fecha_destino" value="{fecha_destino}">
                    <input type="hidden" name="nuevo_turno" value="{nuevo_turno}">
                    <input type="hidden" name="confirmar" value="1">
                    <button type="submit" class="btn btn-warning btn-lg" onclick="return confirm('¿Confirmar cambio de turno?')">✅ Confirmar Cambio</button>
                    <a href="/cambiar_turno" class="btn btn-secondary btn-lg">❌ Cancelar</a>
                </form></div>'''
        else:
            # Execute: delete source
            conn.execute("DELETE FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, fecha))
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                conn.execute("DELETE FROM roles_mensuales WHERE profesional_id=? AND anio=? AND mes=? AND dia=?",
                    (prof_id, dt.year, dt.month, dt.day))
            except: pass

            # If different destination, also clear destination
            if fecha_destino != fecha:
                conn.execute("DELETE FROM citas WHERE profesional_id=? AND fecha=?", (prof_id, fecha_destino))
                try:
                    dt2 = datetime.strptime(fecha_destino, '%Y-%m-%d')
                    conn.execute("DELETE FROM roles_mensuales WHERE profesional_id=? AND anio=? AND mes=? AND dia=?",
                        (prof_id, dt2.year, dt2.month, dt2.day))
                except: pass

            # Update roles_mensuales for destination
            try:
                dt_dest = datetime.strptime(fecha_destino, '%Y-%m-%d')
                conn.execute("INSERT OR REPLACE INTO roles_mensuales (profesional_id, anio, mes, dia, turno) VALUES (?,?,?,?,?)",
                    (prof_id, dt_dest.year, dt_dest.month, dt_dest.day, nuevo_turno))
            except: pass

            # Insert new slots at destination date
            pac_idx = 0
            for slot in new_slots:
                pac=''; dni=''; edad=''; cel=''; obs=''; estado='Disponible'
                tipo=''; app_act=''; asist='Pendiente'; sihce=0; sihce_pid=0; creado=None; modif=None
                if slot['turno'] != 'ADMINISTRATIVA' and pac_idx < len(pacientes):
                    p = pacientes[pac_idx]
                    pac=p['paciente']; dni=p['dni']; edad=p.get('edad','')
                    cel=p['celular']; obs=p['observaciones']; estado='Confirmado'
                    tipo=p['tipo_paciente']; app_act=p.get('actividad_app','')
                    asist=p.get('asistencia','Pendiente')
                    sihce=p.get('sihce',0); sihce_pid=p.get('sihce_prof_id',0)
                    creado=p.get('creado_por'); modif=p.get('modificado_por')
                    pac_idx += 1
                conn.execute("""INSERT INTO citas (profesional_id,fecha,hora_inicio,hora_fin,turno,area,
                    paciente,dni,edad,celular,observaciones,estado,tipo_paciente,actividad_app,
                    asistencia,sihce,sihce_prof_id,creado_por,modificado_por,modificado_en)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (prof_id, fecha_destino, slot['inicio'], slot['fin'], slot['turno'], prof['especialidad'],
                     pac, dni, edad, cel, obs, estado, tipo, app_act, asist, sihce, sihce_pid, creado, modif))

            detalle = f'{prof["nombre"]} | {fecha}→{fecha_destino} | Turno: {nuevo_turno} | {len(pacientes)} pac trasladados'
            conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
                (0, session['user_id'], 'CAMBIO_TURNO', detalle))
            conn.commit()

            perdidos = f' | {len(pacientes_sin_cupo)} no cupieron' if pacientes_sin_cupo else ''
            flash(f'Turno cambiado: {prof["nombre"]} → {nuevo_turno} en {fecha_destino}. {len(pacientes)} pacientes trasladados.{perdidos}', 'success')
            conn.close()
            return redirect('/cambiar_turno')

    conn.close()
    prof_options = ''.join(f'<option value="{p["id"]}">{p["nombre"]} ({p["especialidad"]})</option>' for p in profesionales)
    flash_msgs = session.pop('_flashes', [])
    return page('Cambiar Turno - Sistema de Citas', _cambiar_turno_form(prof_options, resultado), flash_msgs)

def _cambiar_turno_form(prof_options, resultado=''):
    today = datetime.now().strftime('%Y-%m-%d')
    return f'''<div class="page-header"><h2>🔄 Cambiar Turno de Profesional</h2></div>
    <div class="card"><h3>Cambiar o crear turno</h3>
    <form method="POST">
        <input type="hidden" name="accion" value="cambiar">
        <div class="form-row">
            <div class="form-group"><label>Profesional</label>
                <select name="prof_id" class="form-select" required><option value="">— Seleccionar —</option>{prof_options}</select>
            </div>
            <div class="form-group"><label>Fecha origen (día actual del profesional)</label>
                <input type="date" name="fecha" class="form-input" required>
            </div>
            <div class="form-group"><label>Fecha destino (dejar igual si solo cambia turno)</label>
                <input type="date" name="fecha_destino" class="form-input" placeholder="Opcional">
            </div>
            <div class="form-group"><label>Nuevo Turno</label>
                <select name="nuevo_turno" class="form-select" required>
                    <option value="">— Seleccionar —</option>
                    <option value="M">M - Solo Mañana</option>
                    <option value="T">T - Solo Tarde</option>
                    <option value="MT">MT - Mañana y Tarde</option>
                    <option value="GD">GD - Guardia Diurna</option>
                </select>
            </div>
        </div>
        <button type="submit" class="btn btn-warning btn-lg">🔍 Ver Vista Previa</button>
    </form></div>
    <div class="card" style="border:1px solid #c62828"><h3>🗑️ Eliminar cupos de una fecha (corregir errores)</h3>
    <form method="POST">
        <input type="hidden" name="accion" value="eliminar">
        <div class="form-row">
            <div class="form-group"><label>Profesional</label>
                <select name="prof_id" class="form-select" required><option value="">— Seleccionar —</option>{prof_options}</select>
            </div>
            <div class="form-group"><label>Fecha a eliminar</label>
                <input type="date" name="fecha" class="form-input" required>
            </div>
        </div>
        <button type="submit" class="btn btn-danger">🗑️ Eliminar Cupos</button>
    </form></div>
    {resultado}'''


@app.route('/historial')
@admin_required
def historial():
    fecha_desde = request.args.get('desde', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    fecha_hasta = request.args.get('hasta', datetime.now().strftime('%Y-%m-%d'))
    accion_filtro = request.args.get('accion', 'TODAS')
    usuario_filtro = request.args.get('usuario', '0')

    conn = get_db()
    query = """SELECT h.*, u.nombre as usuario_nombre, u.username,
        p.nombre as prof_nombre, c.fecha as cita_fecha, c.hora_inicio, c.paciente
        FROM historial h 
        LEFT JOIN usuarios u ON u.id=h.usuario_id
        LEFT JOIN citas c ON c.id=h.cita_id
        LEFT JOIN profesionales p ON p.id=c.profesional_id
        WHERE DATE(h.fecha_hora) >= ? AND DATE(h.fecha_hora) <= ?"""
    params = [fecha_desde, fecha_hasta]

    if accion_filtro != 'TODAS':
        query += " AND h.accion=?"
        params.append(accion_filtro)
    if usuario_filtro != '0':
        query += " AND h.usuario_id=?"
        params.append(int(usuario_filtro))

    query += " ORDER BY h.fecha_hora DESC LIMIT 500"
    registros = conn.execute(query, params).fetchall()
    usuarios = conn.execute("SELECT id, nombre FROM usuarios ORDER BY nombre").fetchall()
    conn.close()

    rows = ''
    for r in registros:
        try:
            dt = datetime.strptime(r['fecha_hora'][:19], '%Y-%m-%d %H:%M:%S')
            # Convert UTC to Peru time (UTC-5)
            dt = dt - timedelta(hours=5)
            fecha_h = dt.strftime('%d/%m/%Y %H:%M')
        except:
            fecha_h = str(r['fecha_hora'])[:16]

        icon = {'AGENDAR': '📝', 'ELIMINAR': '🗑️', 'EDITAR': '✏️', 'MIGRAR': '📦',
                'REAGENDAR': '📋', 'ASISTENCIA': '✅', 'CAMBIO_TURNO': '🔄',
                'ELIMINAR_CUPOS': '⚠️'}.get(r['accion'], '📌')

        color = {'ELIMINAR': '#c62828', 'ELIMINAR_CUPOS': '#c62828', 'CAMBIO_TURNO': '#e65100',
                 'AGENDAR': '#2e7d32', 'EDITAR': '#1565c0', 'MIGRAR': '#6a1b9a',
                 'REAGENDAR': '#00838f', 'ASISTENCIA': '#33691e'}.get(r['accion'], '#333')

        # Build context info: professional + date + patient
        prof_info = ''
        if r['prof_nombre']:
            prof_info = f'<strong style="color:#1565c0">{r["prof_nombre"]}</strong>'
            if r['cita_fecha']:
                try:
                    dt_c = datetime.strptime(r['cita_fecha'], '%Y-%m-%d')
                    prof_info += f'<br><small style="color:#666">{DIAS_ES[dt_c.weekday()][:3]} {dt_c.day}/{dt_c.month:02d} {r["hora_inicio"] or ""}</small>'
                except: pass
        elif r['accion'] in ('CAMBIO_TURNO', 'ELIMINAR_CUPOS', 'UNIR_TURNOS'):
            # Extract professional from detalle
            detalle = r['detalle'] or ''
            if '|' in detalle:
                prof_info = f'<small style="color:#666">{detalle.split("|")[0].strip()}</small>'

        rows += f'''<tr>
            <td style="font-size:.8rem">{fecha_h}</td>
            <td><strong>{r['usuario_nombre'] or r['username'] or 'Sistema'}</strong></td>
            <td><span style="color:{color};font-weight:700">{icon} {r['accion']}</span></td>
            <td>{prof_info}</td>
            <td style="font-size:.85rem">{r['detalle'] or ''}</td></tr>'''

    if not registros:
        rows = '<tr><td colspan="5" style="text-align:center;color:#666;padding:2rem">No hay registros en este período</td></tr>'

    # Contadores
    total = len(registros)
    eliminados = sum(1 for r in registros if r['accion'] in ('ELIMINAR', 'ELIMINAR_CUPOS'))
    agendados = sum(1 for r in registros if r['accion'] == 'AGENDAR')
    editados = sum(1 for r in registros if r['accion'] == 'EDITAR')
    migrados = sum(1 for r in registros if r['accion'] in ('MIGRAR', 'REAGENDAR'))

    sel_todas = 'selected' if accion_filtro == 'TODAS' else ''
    usr_opts = ''.join(f'<option value="{u["id"]}" {"selected" if str(u["id"])==usuario_filtro else ""}>{u["nombre"]}</option>' for u in usuarios)

    content = f'''<div class="page-header"><h2>📜 Historial de Actividad</h2></div>
    <div class="card no-print" style="padding:1rem">
        <form method="GET" class="filter-row">
            <div class="filter-group"><label>Desde</label><input type="date" name="desde" value="{fecha_desde}" class="form-input"></div>
            <div class="filter-group"><label>Hasta</label><input type="date" name="hasta" value="{fecha_hasta}" class="form-input"></div>
            <div class="filter-group"><label>Acción</label><select name="accion" class="form-select">
                <option value="TODAS" {sel_todas}>Todas</option>
                <option value="AGENDAR" {"selected" if accion_filtro=="AGENDAR" else ""}>📝 Agendar</option>
                <option value="ELIMINAR" {"selected" if accion_filtro=="ELIMINAR" else ""}>🗑️ Eliminar</option>
                <option value="EDITAR" {"selected" if accion_filtro=="EDITAR" else ""}>✏️ Editar</option>
                <option value="MIGRAR" {"selected" if accion_filtro=="MIGRAR" else ""}>📦 Migrar</option>
                <option value="REAGENDAR" {"selected" if accion_filtro=="REAGENDAR" else ""}>📋 Reagendar</option>
                <option value="ASISTENCIA" {"selected" if accion_filtro=="ASISTENCIA" else ""}>✅ Asistencia</option>
                <option value="CAMBIO_TURNO" {"selected" if accion_filtro=="CAMBIO_TURNO" else ""}>🔄 Cambio turno</option>
            </select></div>
            <div class="filter-group"><label>Usuario</label><select name="usuario" class="form-select">
                <option value="0">Todos</option>{usr_opts}</select></div>
            <div class="filter-group" style="align-self:flex-end"><button type="submit" class="btn btn-primary">🔍 Filtrar</button></div>
        </form>
    </div>
    <div class="card" style="padding:.8rem">
        <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem">
            <span style="background:#e8f5e9;padding:.3rem .8rem;border-radius:4px;font-size:.85rem">📝 Agendados: <strong>{agendados}</strong></span>
            <span style="background:#ffebee;padding:.3rem .8rem;border-radius:4px;font-size:.85rem">🗑️ Eliminados: <strong>{eliminados}</strong></span>
            <span style="background:#e3f2fd;padding:.3rem .8rem;border-radius:4px;font-size:.85rem">✏️ Editados: <strong>{editados}</strong></span>
            <span style="background:#f3e5f5;padding:.3rem .8rem;border-radius:4px;font-size:.85rem">📦 Migrados: <strong>{migrados}</strong></span>
            <span style="background:#f5f5f5;padding:.3rem .8rem;border-radius:4px;font-size:.85rem">Total: <strong>{total}</strong></span>
        </div>
        <div class="table-wrapper"><table class="citas-table">
            <thead><tr><th>Fecha/Hora</th><th>Usuario</th><th>Acción</th><th>Profesional / Cita</th><th>Detalle</th></tr></thead>
            <tbody>{rows}</tbody></table></div>
    </div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Historial - Sistema de Citas', content, flash_msgs)

@app.route('/buscar')
@login_required
def buscar_paciente():
    q = request.args.get('q', '').strip().upper()
    mes = request.args.get('mes', '0')
    anio = request.args.get('anio', str(datetime.now().year))
    resultados = ''
    if q and len(q) >= 2:
        conn = get_db()
        if mes != '0':
            citas = conn.execute("""SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.turno, c.paciente, c.dni,
                c.edad, c.celular, c.estado, c.asistencia, c.tipo_paciente, c.area,
                p.nombre as prof_nombre, p.especialidad, p.id as prof_id
                FROM citas c JOIN profesionales p ON p.id=c.profesional_id
                WHERE (c.paciente LIKE ? OR c.dni LIKE ?) AND c.estado='Confirmado'
                AND strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=?
                ORDER BY c.fecha DESC, c.hora_inicio""",
                (f'%{q}%', f'%{q}%', anio, f"{int(mes):02d}")).fetchall()
        else:
            citas = conn.execute("""SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.turno, c.paciente, c.dni,
                c.edad, c.celular, c.estado, c.asistencia, c.tipo_paciente, c.area,
                p.nombre as prof_nombre, p.especialidad, p.id as prof_id
                FROM citas c JOIN profesionales p ON p.id=c.profesional_id
                WHERE (c.paciente LIKE ? OR c.dni LIKE ?) AND c.estado='Confirmado'
                ORDER BY c.fecha DESC, c.hora_inicio""",
                (f'%{q}%', f'%{q}%')).fetchall()
        conn.close()

        if citas:
            rows = ''
            for c in citas:
                try:
                    dt = datetime.strptime(c['fecha'], '%Y-%m-%d')
                    fecha_d = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]}"
                except: fecha_d = c['fecha']
                asist_icon = '✅' if c['asistencia'] == 'Asistió' else ('❌' if c['asistencia'] == 'No asistió' else '⏳')
                rows += f'''<tr>
                    <td><strong>{c['paciente']}</strong><br><small>{c['dni']}</small></td>
                    <td><strong>{fecha_d}</strong></td>
                    <td>{c['hora_inicio']}</td>
                    <td>{c['turno']}</td>
                    <td>{c['area']}</td>
                    <td>{c['prof_nombre']}</td>
                    <td>{asist_icon} {c['asistencia']}</td>
                    <td>
                        <a href="/?prof_id={c['prof_id']}&fecha={c['fecha']}" class="btn btn-sm btn-primary" title="Ver en agenda">📅</a>
                        <a href="/cita/imprimir/{c['id']}" target="_blank" class="btn btn-sm btn-secondary" title="Imprimir">🖨️</a>
                    </td></tr>'''
            mes_label = f' en {MESES_ES[int(mes)]} {anio}' if mes != '0' else ''
            resultados = f'''<div class="card"><h3>Se encontraron {len(citas)} cita(s){mes_label}</h3>
                <div class="table-wrapper"><table class="citas-table">
                <thead><tr><th>Paciente</th><th>Fecha</th><th>Hora</th><th>Turno</th><th>Área</th><th>Profesional</th><th>Asistencia</th><th>Acciones</th></tr></thead>
                <tbody>{rows}</tbody></table></div></div>'''
        else:
            resultados = '<div class="card"><p style="text-align:center;color:#666;padding:2rem">No se encontraron resultados para "<strong>' + q + '</strong>"</p></div>'

    month_opts = f'<option value="0">Todos los meses</option>' + ''.join([f'<option value="{i}" {"selected" if mes==str(i) else ""}>{MESES_ES[i]}</option>' for i in range(1, 13)])

    content = f'''<div class="page-header"><h2>🔍 Buscar Paciente</h2></div>
    <div class="card">
        <form method="GET">
            <div class="form-row">
                <div class="form-group" style="flex:3"><label>Buscar por nombre o DNI</label>
                    <input type="text" name="q" class="form-input" value="{q}" placeholder="Escriba nombre o DNI del paciente..." autofocus>
                </div>
                <div class="form-group" style="flex:1"><label>Mes</label>
                    <select name="mes" class="form-select">{month_opts}</select>
                </div>
                <div class="form-group" style="flex:1"><label>Año</label>
                    <input type="number" name="anio" class="form-input" value="{anio}" min="2024" max="2030">
                </div>
                <div class="form-group" style="flex:1;display:flex;align-items:flex-end">
                    <button type="submit" class="btn btn-primary btn-lg" style="width:100%">🔍 Buscar</button>
                </div>
            </div>
        </form>
    </div>
    {resultados}'''
    flash_msgs = session.pop('_flashes', [])
    return page('Buscar Paciente', content, flash_msgs)

@app.route('/cita/editar/<int:cita_id>', methods=['GET', 'POST'])
@login_required
def editar_cita(cita_id):
    if session.get('user_rol') == 'lector':
        flash('No tiene permisos (solo lectura)', 'danger')
        return redirect('/')
    conn = get_db()
    cita = dict(conn.execute("SELECT c.*, p.nombre as prof_nombre FROM citas c JOIN profesionales p ON p.id=c.profesional_id WHERE c.id=?", (cita_id,)).fetchone())

    if request.method == 'POST':
        tipo = request.form.get('tipo_paciente', 'NUEVO')
        paciente = request.form.get('paciente', '').strip().upper()
        actividad_app = request.form.get('actividad_app', '').strip()
        if actividad_app == 'OTRO':
            actividad_app = request.form.get('actividad_app_manual', '').strip().upper()
        if tipo == 'ADMINISTRATIVA':
            paciente = paciente or 'HORA ADMINISTRATIVA'
        elif tipo == 'APP':
            paciente = paciente or actividad_app or 'ACTIVIDAD APP'
        conn.execute("""UPDATE citas SET paciente=?, dni=?, edad=?, celular=?, observaciones=?,
            tipo_paciente=?, actividad_app=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?""",
            (paciente, request.form.get('dni','').strip(),
             request.form.get('edad','').strip(), request.form.get('celular','').strip(),
             request.form.get('observaciones','').strip(), tipo,
             actividad_app, session['user_id'], cita_id))
        conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
            (cita_id, session['user_id'], 'EDITAR', f'Editado: {request.form.get("paciente","")}'))
        conn.commit(); conn.close()
        flash('Datos del paciente actualizados', 'success')
        return redirect(f'/?prof_id={cita["profesional_id"]}&fecha={cita["fecha"]}')

    conn.close()
    try:
        dt = datetime.strptime(cita['fecha'], '%Y-%m-%d')
        fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
    except: fecha_display = cita['fecha']

    sel_nuevo = 'selected' if cita.get('tipo_paciente') == 'NUEVO' else ''
    sel_cont = 'selected' if cita.get('tipo_paciente') == 'CONTINUADOR' else ''
    sel_app = 'selected' if cita.get('tipo_paciente') == 'APP' else ''
    sel_admin = 'selected' if cita.get('tipo_paciente') == 'ADMINISTRATIVA' else ''
    app_val = cita.get('actividad_app', '')

    content = f'''<div class="page-header"><h2>✏️ Editar Paciente</h2></div>
    <div class="card">
        <p><strong>Profesional:</strong> {cita['prof_nombre']} | <strong>Fecha:</strong> {fecha_display} | <strong>Hora:</strong> {cita['hora_inicio']} - {cita['hora_fin']}</p>
        <form method="POST" style="margin-top:1rem">
            <div class="form-row">
                <div class="form-group"><label>Paciente</label><input type="text" name="paciente" class="form-input" value="{cita['paciente']}"></div>
                <div class="form-group"><label>DNI</label><input type="text" name="dni" class="form-input" maxlength="8" value="{cita['dni']}"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Edad</label><input type="text" name="edad" class="form-input" maxlength="3" value="{cita.get('edad','')}"></div>
                <div class="form-group"><label>Celular</label><input type="text" name="celular" class="form-input" maxlength="9" value="{cita['celular']}"></div>
                <div class="form-group"><label>Tipo</label><select name="tipo_paciente" class="form-select">
                    <option value="NUEVO" {sel_nuevo}>NUEVO</option>
                    <option value="CONTINUADOR" {sel_cont}>CONTINUADOR</option>
                    <option value="APP" {sel_app}>APP (Actividad Preventiva)</option>
                    <option value="ADMINISTRATIVA" {sel_admin}>HORA ADMINISTRATIVA</option>
                </select></div>
            </div>
            <div class="form-group"><label>Observaciones</label><input type="text" name="observaciones" class="form-input" value="{cita.get('observaciones','')}"></div>
            <div class="form-group"><label>Actividad APP</label><select name="actividad_app" class="form-select" onchange="document.getElementById('edit-app-manual').style.display=(this.value==='OTRO')?'block':'none'">
                <option value="">No aplica</option>
                <option value="VISITA DOMICILIARIA" {'selected' if app_val=='VISITA DOMICILIARIA' else ''}>Visita domiciliaria</option>
                <option value="SEGUIMIENTO A USUARIOS" {'selected' if app_val=='SEGUIMIENTO A USUARIOS' else ''}>Seguimiento a usuarios</option>
                <option value="GAM ADULTO" {'selected' if app_val=='GAM ADULTO' else ''}>GAM adulto</option>
                <option value="GAM NIÑO" {'selected' if app_val=='GAM NIÑO' else ''}>GAM niño</option>
                <option value="GAM ADICCIONES" {'selected' if app_val=='GAM ADICCIONES' else ''}>GAM adicciones</option>
                <option value="HOGAR PROTEGIDO" {'selected' if app_val=='HOGAR PROTEGIDO' else ''}>Hogar protegido</option>
                <option value="CHARLA RADIAL" {'selected' if app_val=='CHARLA RADIAL' else ''}>Charla radial</option>
                <option value="CHARLA EN COMUNIDAD" {'selected' if app_val=='CHARLA EN COMUNIDAD' else ''}>Charla en comunidad</option>
                <option value="REALIZACIÓN DE INFORMES" {'selected' if app_val=='REALIZACIÓN DE INFORMES' else ''}>Realización de Informes</option>
                <option value="REUNIÓN DE PERSONAL" {'selected' if app_val=='REUNIÓN DE PERSONAL' else ''}>Reunión de personal</option>
                <option value="OTRO" {'selected' if app_val and app_val not in ('VISITA DOMICILIARIA','SEGUIMIENTO A USUARIOS','GAM ADULTO','GAM NIÑO','GAM ADICCIONES','HOGAR PROTEGIDO','CHARLA RADIAL','CHARLA EN COMUNIDAD','REALIZACIÓN DE INFORMES','REUNIÓN DE PERSONAL','REUNIÓN PROTOCOLO ACTUACIÓN CONJUNTA','REUNIÓN ASOCIACIÓN FAMILIARES','REUNIÓN TÉCNICA COMITÉ SALUD MENTAL') else ''}>Otro (escribir)</option>
            </select></div>
            <div id="edit-app-manual" class="form-group" style="display:{'block' if app_val and app_val not in ('VISITA DOMICILIARIA','SEGUIMIENTO A USUARIOS','GAM ADULTO','GAM NIÑO','GAM ADICCIONES','HOGAR PROTEGIDO','CHARLA RADIAL','CHARLA EN COMUNIDAD','REALIZACIÓN DE INFORMES','REUNIÓN DE PERSONAL','REUNIÓN PROTOCOLO ACTUACIÓN CONJUNTA','REUNIÓN ASOCIACIÓN FAMILIARES','REUNIÓN TÉCNICA COMITÉ SALUD MENTAL','') else 'none'}">
                <label>Describir actividad</label><input type="text" name="actividad_app_manual" class="form-input" value="{app_val if app_val and app_val not in ('VISITA DOMICILIARIA','SEGUIMIENTO A USUARIOS','GAM ADULTO','GAM NIÑO','GAM ADICCIONES','HOGAR PROTEGIDO','CHARLA RADIAL','CHARLA EN COMUNIDAD','REALIZACIÓN DE INFORMES','REUNIÓN DE PERSONAL','REUNIÓN PROTOCOLO ACTUACIÓN CONJUNTA','REUNIÓN ASOCIACIÓN FAMILIARES','REUNIÓN TÉCNICA COMITÉ SALUD MENTAL') else ''}"></div>
            <div class="form-actions">
                <button type="submit" class="btn btn-success">💾 Guardar Cambios</button>
                <a href="/?prof_id={cita['profesional_id']}&fecha={cita['fecha']}" class="btn btn-secondary">Cancelar</a>
            </div>
        </form>
    </div>'''
    return page('Editar Paciente', content)


@app.route('/cita/migrar/<int:cita_id>', methods=['GET', 'POST'])
@login_required
def migrar_cita(cita_id):
    if session.get('user_rol') == 'lector':
        flash('No tiene permisos (solo lectura)', 'danger')
        return redirect('/')
    conn = get_db()
    cita = dict(conn.execute("SELECT c.*, p.nombre as prof_nombre FROM citas c JOIN profesionales p ON p.id=c.profesional_id WHERE c.id=?", (cita_id,)).fetchone())
    profesionales = conn.execute("SELECT id, nombre, especialidad FROM profesionales WHERE activo=1 ORDER BY CASE especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, orden").fetchall()

    if request.method == 'POST':
        dest_id = int(request.form.get('dest_cita_id', 0))
        accion = request.form.get('accion', 'mover')
        if not dest_id:
            flash('Seleccione un cupo destino', 'danger')
            conn.close()
            return redirect(f'/cita/migrar/{cita_id}')

        dest = conn.execute("SELECT * FROM citas WHERE id=? AND estado='Disponible'", (dest_id,)).fetchone()
        if not dest:
            flash('El cupo destino no esta disponible', 'danger')
            conn.close()
            return redirect(f'/cita/migrar/{cita_id}')

        conn.execute("""UPDATE citas SET paciente=?, dni=?, edad=?, celular=?, observaciones=?,
            estado='Confirmado', tipo_paciente=?, actividad_app=?, sihce=?, sihce_prof_id=?,
            creado_por=?, modificado_por=?, modificado_en=CURRENT_TIMESTAMP WHERE id=?""",
            (cita['paciente'], cita['dni'], cita.get('edad',''), cita['celular'],
             cita.get('observaciones',''), cita.get('tipo_paciente',''), cita.get('actividad_app',''),
             cita.get('sihce',0), cita.get('sihce_prof_id',0),
             cita.get('creado_por'), session['user_id'], dest_id))

        if accion == 'mover':
            conn.execute("""UPDATE citas SET paciente='',dni='',edad='',celular='',observaciones='',
                estado='Disponible',tipo_paciente='',actividad_app='',asistencia='Pendiente',
                sihce=0,sihce_prof_id=0,modificado_por=?,modificado_en=CURRENT_TIMESTAMP WHERE id=?""",
                (session['user_id'], cita_id))
            conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
                (cita_id, session['user_id'], 'MIGRAR', f'{cita["paciente"]} movido a cupo {dest_id}'))
            flash(f'Paciente {cita["paciente"]} migrado exitosamente', 'success')
        else:
            conn.execute("INSERT INTO historial (cita_id, usuario_id, accion, detalle) VALUES (?,?,?,?)",
                (dest_id, session['user_id'], 'REAGENDAR', f'{cita["paciente"]} copiado desde cupo {cita_id}'))
            flash(f'Paciente {cita["paciente"]} reagendado (cita original se mantiene)', 'success')

        conn.commit(); conn.close()
        return redirect(f'/?prof_id={dest["profesional_id"]}&fecha={dest["fecha"]}')

    dest_prof = request.args.get('dest_prof', '')
    dest_fecha = request.args.get('dest_fecha', '')
    cupos_html = ''
    if dest_prof and dest_fecha:
        cupos = conn.execute("""SELECT c.id, c.hora_inicio, c.hora_fin, c.turno FROM citas c
            WHERE c.profesional_id=? AND c.fecha=? AND c.estado='Disponible' AND c.turno!='ADMINISTRATIVA'
            ORDER BY c.hora_inicio""", (dest_prof, dest_fecha)).fetchall()
        if cupos:
            cupos_html = '<div class="form-group"><label>Cupo destino</label><select name="dest_cita_id" class="form-select" required><option value="">Seleccionar hora</option>'
            for cu in cupos:
                cupos_html += f'<option value="{cu["id"]}">{cu["hora_inicio"]} - {cu["hora_fin"]} ({cu["turno"]})</option>'
            cupos_html += '</select></div>'
        else:
            cupos_html = '<p style="color:#c62828;font-weight:bold">No hay cupos disponibles en esa fecha</p>'

    conn.close()
    try:
        dt = datetime.strptime(cita['fecha'], '%Y-%m-%d')
        fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
    except: fecha_display = cita['fecha']

    prof_opts = ''.join(f'<option value="{p["id"]}" {"selected" if str(p["id"])==dest_prof else ""}>{p["nombre"]} ({p["especialidad"]})</option>' for p in profesionales)

    cupos_form = ''
    if cupos_html:
        cupos_form = f'''<div class="card"><h3>Cupos disponibles</h3>
        <form method="POST">
            {cupos_html}
            <div class="form-group" style="margin-top:1rem"><label>Accion</label><select name="accion" class="form-select">
                <option value="mover">Mover (libera cupo original)</option>
                <option value="copiar">Reagendar (mantiene cita original)</option>
            </select></div>
            <button type="submit" class="btn btn-success btn-lg" style="margin-top:.5rem" onclick="return confirm('Confirmar?')">Confirmar</button>
            <a href="/?prof_id={cita['profesional_id']}&fecha={cita['fecha']}" class="btn btn-secondary">Cancelar</a>
        </form></div>'''

    content = f'''<div class="page-header"><h2>📦 Migrar / Reagendar Paciente</h2></div>
    <div class="card" style="background:#eff6ff;border:2px solid #2b5797">
        <h3>Paciente actual</h3>
        <p><strong>{cita['paciente']}</strong> | DNI: {cita['dni']} | {cita['prof_nombre']}</p>
        <p>{fecha_display} | {cita['hora_inicio']} - {cita['hora_fin']} | {cita['turno']}</p>
    </div>
    <div class="card"><h3>Seleccionar destino</h3>
    <form method="GET">
        <div class="form-row">
            <div class="form-group"><label>Profesional destino</label>
                <select name="dest_prof" class="form-select" required><option value="">Seleccionar</option>{prof_opts}</select>
            </div>
            <div class="form-group"><label>Fecha destino</label>
                <input type="date" name="dest_fecha" class="form-input" value="{dest_fecha}" required>
            </div>
        </div>
        <button type="submit" class="btn btn-primary">Buscar Cupos</button>
    </form></div>
    {cupos_form}'''
    return page('Migrar Paciente', content)


@app.route('/cita/imprimir/<int:cita_id>')
@login_required
def imprimir_cita(cita_id):
    conn = get_db()
    cita = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.especialidad
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE c.id=?""", (cita_id,)).fetchone()
    if not cita:
        conn.close()
        return "Cita no encontrada", 404

    cita = dict(cita)

    sihce_info = ''
    if cita['sihce'] and cita.get('sihce_prof_id'):
        sp = conn.execute("SELECT nombre FROM profesionales WHERE id=?", (cita['sihce_prof_id'],)).fetchone()
        if sp: sihce_info = f'<tr><td><strong>SIHCE con:</strong></td><td>{sp["nombre"]}</td></tr>'
    conn.close()

    try:
        dt = datetime.strptime(cita['fecha'], '%Y-%m-%d')
        fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
    except:
        fecha_display = cita['fecha']

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Cita - {cita['paciente']}</title>
<style>
    @page {{ size: A5; margin: 10mm; }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: Arial, sans-serif; font-size: 12px; padding: 10mm; max-width: 148mm; }}
    .header {{ text-align: center; border-bottom: 2px solid #1a365d; padding-bottom: 8px; margin-bottom: 12px; }}
    .header h1 {{ font-size: 14px; color: #1a365d; }}
    .titulo {{ background: #1a365d; color: white; text-align: center; padding: 6px; font-size: 13px; font-weight: bold; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 5px 10px; border: 1px solid #ddd; }}
    td:first-child {{ width: 30%; font-weight: bold; background: #f0f0f0; font-size: 11px; }}
    .grande {{ font-size: 16px; font-weight: bold; text-transform: uppercase; }}
    .nota {{ margin-top: 20px; text-align: center; padding: 8px; background: #fff3e0; border: 1px solid #ff8f00; border-radius: 4px; font-weight: bold; font-size: 12px; color: #e65100; }}
    .footer {{ margin-top: 12px; text-align: center; font-size: 8px; color: #999; }}
    @media print {{ .no-print {{ display: none !important; }} }}
</style></head><body>
    <div class="no-print" style="text-align:center;margin-bottom:10px">
        <button onclick="window.print()" style="padding:8px 20px;font-size:13px;background:#1a365d;color:white;border:none;border-radius:4px;cursor:pointer">🖨️ Imprimir</button>
        <button onclick="window.close()" style="padding:8px 20px;font-size:13px;background:#e2e8f0;border:none;border-radius:4px;cursor:pointer;margin-left:5px">Cerrar</button>
    </div>
    <div class="header"><h1>🏥 CENTRO DE SALUD MENTAL COMUNITARIO</h1></div>
    <div class="titulo">COMPROBANTE DE CITA</div>
    <table>
        <tr><td>Paciente:</td><td>{cita['paciente']}</td></tr>
        <tr><td>DNI:</td><td>{cita['dni']}</td></tr>
        <tr><td>Fecha:</td><td class="grande">{fecha_display}</td></tr>
        <tr><td>Hora:</td><td style="font-size:14px;font-weight:bold">{cita['hora_inicio']}</td></tr>
        <tr><td>Turno:</td><td>{cita['turno']}</td></tr>
        <tr><td>Área:</td><td class="grande">{cita['area']}</td></tr>
        <tr><td>Profesional:</td><td>{cita['prof_nombre']}</td></tr>
    </table>
    <div class="nota">⚠️ ASISTIR A SU CITA 15 MINUTOS ANTES</div>
    <div class="footer">Sistema de Citas CSMC — {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</body></html>'''
    return html


@app.route('/reporte_diario')
@login_required
def reporte_diario():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    turno_filtro = request.args.get('turno', 'TODOS')
    conn = get_db()
    if turno_filtro == 'MAÑANA':
        citas = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.especialidad, p.color_bg, p.color_font
            FROM citas c JOIN profesionales p ON p.id=c.profesional_id
            WHERE c.fecha=? AND c.estado='Confirmado' AND c.turno='MAÑANA'
            ORDER BY CASE p.especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, p.orden, c.hora_inicio""", (fecha,)).fetchall()
    elif turno_filtro == 'TARDE':
        citas = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.especialidad, p.color_bg, p.color_font
            FROM citas c JOIN profesionales p ON p.id=c.profesional_id
            WHERE c.fecha=? AND c.estado='Confirmado' AND c.turno='TARDE'
            ORDER BY CASE p.especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, p.orden, c.hora_inicio""", (fecha,)).fetchall()
    else:
        citas = conn.execute("""SELECT c.*, p.nombre as prof_nombre, p.especialidad, p.color_bg, p.color_font
            FROM citas c JOIN profesionales p ON p.id=c.profesional_id
            WHERE c.fecha=? AND c.estado='Confirmado'
            ORDER BY CASE p.especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, p.orden, c.turno, c.hora_inicio""", (fecha,)).fetchall()

    try:
        dt = datetime.strptime(fecha, '%Y-%m-%d')
        fecha_display = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month]} {dt.year}"
    except: fecha_display = fecha

    rows = ''
    current_prof = ''
    num = 0
    for c in citas:
        if c['prof_nombre'] != current_prof:
            current_prof = c['prof_nombre']
            num = 0
            rows += f'''<tr style="background:{c['color_bg']};color:{c['color_font']}">
                <td colspan="9" style="padding:.6rem;font-weight:700">{c['prof_nombre']} — {c['especialidad']}</td></tr>'''
        num += 1
        sihce_tag = ''
        if c['sihce']:
            sihce_tag = ' <span class="sihce-tag">SIHCE</span>'
            sp_id = c['sihce_prof_id'] if c['sihce_prof_id'] else 0
            if sp_id:
                sp = conn.execute("SELECT nombre FROM profesionales WHERE id=?", (sp_id,)).fetchone()
                if sp: sihce_tag += f' <small style="color:#e65100">🔗 {sp["nombre"]}</small>'
        app_tag = f'<br><small style="color:#e65100">APP: {c["actividad_app"]}</small>' if c['actividad_app'] else ''
        # Asistencia buttons (same as agenda)
        asist = c['asistencia'] or 'Pendiente'
        si_active = 'btn-asist-active' if asist == 'Asistió' else ''
        no_active = 'btn-asist-no-active' if asist == 'No asistió' else ''
        tp_pend = c['tipo_paciente'] if c['tipo_paciente'] else ''
        pend_rd = 'pendiente' if asist not in ('Asistió', 'No asistió') and tp_pend not in ('APP', 'ADMINISTRATIVA') else ''
        asist_html = f'''<div class="asistencia-btns {pend_rd}" style="display:flex;gap:2px;width:fit-content">
            <button onclick="markAsist({c['id']},'Asistió',this)" class="btn-asist {si_active}" title="Asistió (clic para desmarcar)">✅</button>
            <button onclick="markAsist({c['id']},'No asistió',this)" class="btn-asist {no_active}" title="No asistió (clic para desmarcar)">❌</button>
        </div>'''
        # Red row for APP/ADMINISTRATIVA (same as agenda)
        tp = c['tipo_paciente'] if c['tipo_paciente'] else ''
        row_cls = 'row-app' if tp in ('APP','ADMINISTRATIVA') else ''
        rows += f'''<tr class="{row_cls}"><td>{num}</td><td>{c['turno']}</td>
            <td class="td-hora">{c['hora_inicio']} - {c['hora_fin']}</td>
            <td><strong>{c['paciente']}</strong>{sihce_tag}{app_tag}</td><td>{c['dni']}</td><td>{c['edad']}</td>
            <td><span class="badge {'badge-new' if c['tipo_paciente']=='NUEVO' else 'badge-cont'}">{c['tipo_paciente']}</span></td>
            <td>{c['observaciones']}</td>
            <td>{asist_html}</td></tr>'''

    conn.close()
    if not citas:
        rows = '<tr><td colspan="9" class="text-center">No hay pacientes programados para esta fecha</td></tr>'

    turno_label = 'Todos los turnos' if turno_filtro == 'TODOS' else f'Turno {turno_filtro}'
    sel_todos = 'selected' if turno_filtro == 'TODOS' else ''
    sel_man = 'selected' if turno_filtro == 'MAÑANA' else ''
    sel_tar = 'selected' if turno_filtro == 'TARDE' else ''

    content = f'''<div class="page-header"><h2>📋 Reporte Diario - Pacientes Programados</h2>
        <p class="text-muted" style="font-size:.9rem">Para sacar historias clínicas</p></div>
    <div class="card no-print" style="padding:1rem">
        <form method="GET" class="filter-row">
            <div class="filter-group"><label>Fecha</label><input type="date" name="fecha" value="{fecha}" class="form-input"></div>
            <div class="filter-group"><label>Turno</label><select name="turno" class="form-select">
                <option value="TODOS" {sel_todos}>Todos</option>
                <option value="MAÑANA" {sel_man}>☀️ Mañana</option>
                <option value="TARDE" {sel_tar}>🌙 Tarde</option>
            </select></div>
            <div class="filter-group" style="align-self:flex-end"><button type="submit" class="btn btn-primary">🔍 Consultar</button>
            <button type="button" class="btn btn-secondary" onclick="window.print()">🖨️ Imprimir</button></div>
        </form>
    </div>
    <div class="card">
        <h3>📅 {fecha_display} — {turno_label} — {len(citas)} pacientes</h3>
        <div class="table-wrapper"><table class="citas-table"><thead><tr>
            <th>#</th><th>Turno</th><th>Hora</th><th>Paciente</th><th>DNI</th><th>Edad</th><th>Tipo</th><th>Observaciones</th><th class="no-print">Asistencia</th>
        </tr></thead><tbody>{rows}</tbody></table></div>
    </div>
    <script>
    function markAsist(id, val, btn){{
        var isActive=btn&&(btn.classList.contains('btn-asist-active')||btn.classList.contains('btn-asist-no-active'));
        var current=isActive?'Pendiente':val;
        fetch('/cita/asistencia/'+id+'/'+encodeURIComponent(current), {{method:'POST'}})
            .then(function(r){{if(r.ok)location.reload()}})
            .catch(function(e){{alert('Error: '+e)}});
    }}
    </script>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Reporte Diario - Sistema de Citas', content, flash_msgs, show_asist_banner=True)

# ==============================================================================
# GENERAR CALENDARIO
# ==============================================================================
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
        flash(f'✅ Generados {count} cupos para {MESES_ES[month]} {year}', 'success')
        return redirect('/')

    month_opts = ''.join([f'<option value="{i}" {"selected" if i==datetime.now().month else ""}>{MESES_ES[i]}</option>' for i in range(1, 13)])

    content = f'''<div class="page-header"><h2>⚙️ Generar Calendario Mensual</h2></div>
    <div class="card"><form method="POST">
        <div class="form-row">
            <div class="form-group"><label>Año</label><input type="number" name="year" value="{datetime.now().year}" class="form-input" min="2024" max="2030"></div>
            <div class="form-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
        </div>
        <div class="form-group"><label>Texto del Rol Mensual</label>
            <textarea name="roster_text" class="form-textarea" rows="16">{get_default_roster()}</textarea>
            <small class="form-help">Formato: NOMBRE: Día X TURNO. Turnos: M=Mañana, T=Tarde, MT=Mañana+Tarde, GD=Guardia Diurna.<br>
            ⚠️ M: mañana + hora administrativa | T: inicia 1:30pm | MT y GD: mismo horario completo<br>
            ⚠️ Si ya existen citas agendadas, se migrarán automáticamente.</small>
        </div>
        <div class="form-actions"><button type="submit" class="btn btn-danger btn-lg" onclick="return confirm('¿Generar cupos? Las citas existentes se migrarán al nuevo horario.')">🔄 REGENERAR CALENDARIO</button></div>
    </form></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Generar - Sistema de Citas', content, flash_msgs)

# ==============================================================================
# PROFESIONALES
# ==============================================================================
@app.route('/profesionales')
@admin_required
def profesionales():
    conn = get_db()
    profs = conn.execute("SELECT * FROM profesionales ORDER BY CASE especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, orden").fetchall()
    conn.close()

    rows = ''
    for p in profs:
        inactive = 'row-inactive' if not p['activo'] else ''
        status_badge = '<span class="badge badge-success">Activo</span>' if p['activo'] else '<span class="badge badge-danger">Inactivo</span>'
        btn_text = '⏸️' if p['activo'] else '▶️'
        btn_class = 'btn-warning' if p['activo'] else 'btn-success'
        esp_opts = ''
        for esp in ['PSICOLOGÍA', 'MEDICINA', 'PSIQUIATRÍA', 'TERAPIA OCUPACIONAL', 'TERAPIA DE LENGUAJE', 'SIHCE']:
            sel = 'selected' if p['especialidad'] == esp else ''
            esp_opts += f'<option value="{esp}" {sel}>{esp}</option>'
        font_b = 'selected' if p['color_font'] == 'black' else ''
        font_w = 'selected' if p['color_font'] == 'white' else ''
        rows += f'''<tr class="{inactive}">
            <td><span class="color-swatch" style="background:{p['color_bg']};color:{p['color_font']}">Aa</span></td>
            <td><strong>{p['nombre']}</strong></td><td>{p['especialidad']}</td><td>{status_badge}</td>
            <td style="white-space:nowrap">
                <button class="btn btn-sm btn-primary" onclick="document.getElementById('edit-{p['id']}').style.display=document.getElementById('edit-{p['id']}').style.display==='none'?'table-row':'none'">✏️</button>
                <form method="POST" action="/profesional/toggle/{p['id']}" style="display:inline"><button type="submit" class="btn btn-sm {btn_class}">{btn_text}</button></form>
            </td></tr>
            <tr id="edit-{p['id']}" style="display:none;background:#f0f9ff">
            <td colspan="5">
                <form method="POST" action="/profesional/editar/{p['id']}" style="display:flex;gap:.5rem;align-items:flex-end;flex-wrap:wrap;padding:.5rem">
                    <div class="form-group" style="flex:2;margin:0"><label>Nombre</label><input type="text" name="nombre" value="{p['nombre']}" class="form-input" required></div>
                    <div class="form-group" style="flex:1;margin:0"><label>Especialidad</label><select name="especialidad" class="form-select">{esp_opts}</select></div>
                    <div class="form-group" style="margin:0"><label>Color</label><input type="color" name="color_bg" value="{p['color_bg']}" class="form-color"></div>
                    <div class="form-group" style="margin:0"><label>Texto</label><select name="color_font" class="form-select"><option value="black" {font_b}>Negro</option><option value="white" {font_w}>Blanco</option></select></div>
                    <button type="submit" class="btn btn-sm btn-success">💾 Guardar</button>
                </form>
            </td></tr>'''

    content = f'''<div class="page-header"><h2>👥 Gestión de Profesionales</h2></div>
    <div class="card"><h3>Agregar Profesional</h3>
    <form method="POST" action="/profesional/nuevo">
        <div class="form-row">
            <div class="form-group" style="flex:2"><label>Nombre completo</label><input type="text" name="nombre" class="form-input" required placeholder="APELLIDO APELLIDO NOMBRE NOMBRE"></div>
            <div class="form-group"><label>Especialidad</label><select name="especialidad" class="form-select">{ESPECIALIDADES_OPTIONS}</select></div>
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

@app.route('/profesional/editar/<int:prof_id>', methods=['POST'])
@admin_required
def editar_profesional(prof_id):
    nombre = request.form.get('nombre', '').strip().upper()
    esp = request.form.get('especialidad', 'PSICOLOGÍA')
    color_bg = request.form.get('color_bg', '#CCCCCC')
    color_font = request.form.get('color_font', 'black')
    if not nombre:
        flash('El nombre es obligatorio', 'danger')
        return redirect('/profesionales')
    conn = get_db()
    conn.execute("UPDATE profesionales SET nombre=?, especialidad=?, color_bg=?, color_font=? WHERE id=?",
        (nombre, esp, color_bg, color_font, prof_id))
    conn.commit(); conn.close()
    flash(f'Profesional actualizado: {nombre}', 'success')
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

# ==============================================================================
# USUARIOS
# ==============================================================================
@app.route('/usuarios')
@admin_required
def usuarios():
    conn = get_db()
    users = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
    conn.close()
    rows = ''
    for u in users:
        inactive = 'row-inactive' if not u['activo'] else ''
        role_badge = '<span class="badge badge-admin">ADMIN</span>' if u['rol'] == 'admin' else ('<span class="badge badge-warning">LECTOR</span>' if u['rol'] == 'lector' else '<span class="badge badge-info">OPERADOR</span>')
        status_badge = '<span class="badge badge-success">Activo</span>' if u['activo'] else '<span class="badge badge-danger">Inactivo</span>'
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
            <div class="form-group"><label>Rol</label><select name="rol" class="form-select"><option value="operador">Operador</option><option value="lector">Lector (solo lectura)</option><option value="admin">Administrador</option></select></div>
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

# ==============================================================================
# REPORTES
# ==============================================================================
@app.route('/reportes')
@login_required
def reportes():
    conn = get_db()
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    stats = conn.execute("""SELECT COUNT(*) as total,
        SUM(CASE WHEN estado='Confirmado' AND tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as confirmados,
        SUM(CASE WHEN estado='Disponible' THEN 1 ELSE 0 END) as disponibles,
        SUM(CASE WHEN asistencia='Asistió' AND tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN asistencia='No asistió' AND tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
        SUM(CASE WHEN tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores,
        SUM(CASE WHEN sihce=1 THEN 1 ELSE 0 END) as sihce_total,
        SUM(CASE WHEN tipo_paciente='APP' THEN 1 ELSE 0 END) as total_app,
        SUM(CASE WHEN tipo_paciente='ADMINISTRATIVA' THEN 1 ELSE 0 END) as total_admin
        FROM citas WHERE strftime('%Y',fecha)=? AND strftime('%m',fecha)=? AND turno!='ADMINISTRATIVA'""",
        (str(year), f"{month:02d}")).fetchone()

    by_prof = conn.execute("""SELECT p.nombre, p.color_bg, p.color_font, p.especialidad,
        COUNT(*) as total,
        SUM(CASE WHEN c.estado='Confirmado' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as confirmados,
        SUM(CASE WHEN c.asistencia='Asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN c.asistencia='No asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN c.tipo_paciente='NUEVO' THEN 1 ELSE 0 END) as nuevos,
        SUM(CASE WHEN c.tipo_paciente='CONTINUADOR' THEN 1 ELSE 0 END) as continuadores,
        SUM(CASE WHEN c.sihce=1 THEN 1 ELSE 0 END) as sihce_count,
        SUM(CASE WHEN c.tipo_paciente='APP' THEN 1 ELSE 0 END) as app_count,
        SUM(CASE WHEN c.tipo_paciente='ADMINISTRATIVA' THEN 1 ELSE 0 END) as admin_count
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.turno!='ADMINISTRATIVA'
        GROUP BY p.id ORDER BY CASE p.especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, p.orden""", (str(year), f"{month:02d}")).fetchall()
    conn.close()

    month_opts = ''.join([f'<option value="{i}" {"selected" if i==month else ""}>{MESES_ES[i]}</option>' for i in range(1, 13)])

    total = stats['total'] or 0
    confirmados = stats['confirmados'] or 0
    ocupacion = round(confirmados / total * 100, 1) if total else 0

    stats_html = f'''<div class="stats-grid">
        <div class="stat-card stat-total"><div class="stat-number">{total}</div><div class="stat-label">Total Cupos</div></div>
        <div class="stat-card stat-confirmed"><div class="stat-number">{confirmados}</div><div class="stat-label">Total Citas</div></div>
        <div class="stat-card stat-available"><div class="stat-number">{stats['disponibles'] or 0}</div><div class="stat-label">Disponibles</div></div>
        <div class="stat-card stat-attended"><div class="stat-number">{stats['asistieron'] or 0}</div><div class="stat-label">Asistieron ✅</div></div>
        <div class="stat-card stat-absent"><div class="stat-number">{stats['no_asistieron'] or 0}</div><div class="stat-label">No asistieron ❌</div></div>
        <div class="stat-card stat-new"><div class="stat-number">{stats['nuevos'] or 0}</div><div class="stat-label">Nuevos</div></div>
        <div class="stat-card stat-cont"><div class="stat-number">{stats['continuadores'] or 0}</div><div class="stat-label">Continuadores</div></div>
        <div class="stat-card stat-rate"><div class="stat-number">{ocupacion}%</div><div class="stat-label">Ocupación</div></div>
        <div class="stat-card" style="border-top:4px solid #4caf50"><div class="stat-number">{stats['total_app'] or 0}</div><div class="stat-label">Actividades APP</div></div>
        <div class="stat-card" style="border-top:4px solid #ff9800"><div class="stat-number">{stats['total_admin'] or 0}</div><div class="stat-label">Horas Admin.</div></div>
    </div>'''

    prof_rows = ''
    for p in by_prof:
        pct = round((p['confirmados'] or 0) / p['total'] * 100, 1) if p['total'] else 0
        prof_rows += f'''<tr><td><span class="prof-chip" style="background:{p['color_bg']};color:{p['color_font']}">{p['nombre']}</span></td>
            <td>{p['especialidad']}</td><td><strong>{p['total']}</strong></td><td>{p['confirmados'] or 0}</td>
            <td class="text-success">{p['asistieron'] or 0}</td><td class="text-danger">{p['no_asistieron'] or 0}</td>
            <td>{p['nuevos'] or 0}</td><td>{p['continuadores'] or 0}</td><td>{p['sihce_count'] or 0}</td>
            <td style="color:#4caf50">{p['app_count'] or 0}</td><td style="color:#ff9800">{p['admin_count'] or 0}</td>
            <td><div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div><small>{pct}%</small></td></tr>'''

    content = f'''<div class="page-header"><h2>📊 Reportes y Estadísticas</h2></div>
    <div class="card" style="padding:1rem"><form method="GET" class="filter-row">
        <div class="filter-group"><label>Año</label><input type="number" name="year" value="{year}" class="form-input" min="2024" max="2030"></div>
        <div class="filter-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
        <div class="filter-group" style="align-self:flex-end"><button type="submit" class="btn btn-primary">🔍 Consultar</button></div>
    </form></div>
    {stats_html}
    <div class="card"><h3>📋 Por Profesional</h3><div class="table-wrapper"><table class="citas-table"><thead><tr>
        <th>Profesional</th><th>Especialidad</th><th>Cupos</th><th>Total Citas</th><th>Asistieron</th><th>No asistieron</th><th>Nuevos</th><th>Continuadores</th><th>SIHCE</th><th>APP</th><th>H.Admin</th><th>% Ocupación</th>
    </tr></thead><tbody>{prof_rows}</tbody></table></div></div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Reportes - Sistema de Citas', content, flash_msgs)

# ==============================================================================
# EXPORTAR EXCEL - CON COLORES Y FORMULARIO
# ==============================================================================
@app.route('/inasistencias')
@login_required
def inasistencias():
    conn = get_db()
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    vista = request.args.get('vista', 'profesional')

    ym = (str(year), f"{month:02d}")

    # Ranking por profesional
    ranking = conn.execute("""SELECT p.nombre, p.especialidad, p.color_bg, p.color_font, p.id as prof_id,
        SUM(CASE WHEN c.estado='Confirmado' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as total_citas,
        SUM(CASE WHEN c.asistencia='Asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN c.asistencia='No asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN c.asistencia='Pendiente' AND c.estado='Confirmado' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA') THEN 1 ELSE 0 END) as pendientes,
        SUM(CASE WHEN c.estado='Disponible' THEN 1 ELSE 0 END) as disponibles
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.turno!='ADMINISTRATIVA'
        GROUP BY p.id ORDER BY no_asistieron DESC""", ym).fetchall()

    # Detalle por día
    por_dia = conn.execute("""SELECT c.fecha, p.nombre as prof_nombre, p.especialidad,
        COUNT(*) as total,
        SUM(CASE WHEN c.asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN c.asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.turno!='ADMINISTRATIVA' AND c.estado='Confirmado' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA')
        GROUP BY c.fecha, p.id
        HAVING no_asistieron > 0
        ORDER BY c.fecha, no_asistieron DESC""", ym).fetchall()

    # Lista detallada de pacientes que no asistieron
    no_asist = conn.execute("""SELECT c.fecha, c.hora_inicio, c.turno, c.paciente, c.dni, c.celular,
        p.nombre as prof_nombre, p.especialidad
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.asistencia='No asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA')
        ORDER BY c.fecha DESC, p.orden, c.hora_inicio""", ym).fetchall()
    conn.close()

    # Totales generales
    total_citas = sum(r['total_citas'] or 0 for r in ranking)
    total_no = sum(r['no_asistieron'] or 0 for r in ranking)
    total_si = sum(r['asistieron'] or 0 for r in ranking)
    pct_inasis = round(total_no / total_citas * 100, 1) if total_citas else 0

    # Ranking table
    rank_rows = ''
    for i, r in enumerate(ranking):
        no = r['no_asistieron'] or 0
        tot = r['total_citas'] or 0
        pct = round(no / tot * 100, 1) if tot else 0
        bar_color = '#c62828' if pct > 20 else ('#ff8f00' if pct > 10 else '#2e7d32')
        medal = ['🥇','🥈','🥉'][i] if i < 3 and no > 0 else f'{i+1}'
        disp = r['disponibles'] or 0
        rank_rows += f'''<tr>
            <td style="text-align:center;font-size:1.1rem">{medal}</td>
            <td><span class="prof-chip" style="background:{r['color_bg']};color:{r['color_font']}">{r['nombre']}</span></td>
            <td>{r['especialidad']}</td>
            <td><strong>{tot}</strong></td>
            <td style="color:#2e7d32">{r['asistieron'] or 0}</td>
            <td style="color:#c62828;font-weight:700;font-size:1.1rem">{no}</td>
            <td>{r['pendientes'] or 0}</td>
            <td style="color:#1565c0;font-weight:700">{disp}</td>
            <td><div class="progress-bar"><div class="progress-fill" style="width:{pct}%;background:{bar_color}"></div></div><small style="color:{bar_color}">{pct}%</small></td></tr>'''

    # Por dia table
    dia_rows = ''
    for d in por_dia:
        try:
            dt = datetime.strptime(d['fecha'], '%Y-%m-%d')
            fecha_d = f"{DIAS_ES[dt.weekday()][:3]} {dt.day}"
        except: fecha_d = d['fecha']
        dia_rows += f'<tr><td>{fecha_d}</td><td>{d["prof_nombre"]}</td><td>{d["especialidad"]}</td><td>{d["total"]}</td><td style="color:#c62828;font-weight:700">{d["no_asistieron"]}</td></tr>'

    # Pacientes detalle
    pac_rows = ''
    for p in no_asist:
        try:
            dt = datetime.strptime(p['fecha'], '%Y-%m-%d')
            fecha_d = f"{DIAS_ES[dt.weekday()][:3]} {dt.day}/{dt.month:02d}"
        except: fecha_d = p['fecha']
        pac_rows += f'<tr><td>{fecha_d}</td><td>{p["hora_inicio"]}</td><td>{p["turno"]}</td><td><strong>{p["paciente"]}</strong></td><td>{p["dni"]}</td><td>{p["celular"]}</td><td>{p["prof_nombre"]}</td></tr>'

    month_opts = ''.join([f'<option value="{i}" {"selected" if i==month else ""}>{MESES_ES[i]}</option>' for i in range(1, 13)])
    excel_btn_inasist = '' if session.get('user_rol') == 'lector' else f'<a href="/exportar_inasistencias?year={year}&month={month}" class="btn btn-success">📥 Excel</a>'

    content = f'''<div class="page-header"><h2>📉 Reporte de Inasistencias</h2></div>
    <div class="card no-print" style="padding:1rem"><form method="GET" class="filter-row">
        <div class="filter-group"><label>Año</label><input type="number" name="year" value="{year}" class="form-input" min="2024" max="2030"></div>
        <div class="filter-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
        <div class="filter-group" style="align-self:flex-end"><button type="submit" class="btn btn-primary">🔍 Consultar</button>
        {excel_btn_inasist}
        <button type="button" class="btn btn-secondary" onclick="window.print()">🖨️ Imprimir</button></div>
    </form></div>

    <div class="stats-grid">
        <div class="stat-card stat-total"><div class="stat-number">{total_citas}</div><div class="stat-label">Total Citas</div></div>
        <div class="stat-card stat-attended"><div class="stat-number">{total_si}</div><div class="stat-label">Asistieron ✅</div></div>
        <div class="stat-card stat-absent"><div class="stat-number">{total_no}</div><div class="stat-label">No Asistieron ❌</div></div>
        <div class="stat-card stat-rate"><div class="stat-number" style="color:#c62828">{pct_inasis}%</div><div class="stat-label">% Inasistencia</div></div>
    </div>

    <div class="card" style="padding:1rem">
        <h3>📊 Dashboard de Inasistencias</h3>
        <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:1rem">
            <div style="flex:1;min-width:300px">
                <h4 style="font-size:.9rem;color:#666;margin-bottom:.5rem">% Inasistencia por Profesional</h4>
                <div style="display:flex;flex-direction:column;gap:6px">'''

    for r in ranking:
        no = r['no_asistieron'] or 0
        tot = r['total_citas'] or 0
        pct = round(no / tot * 100, 1) if tot else 0
        bar_w = min(pct * 3, 100)
        bar_c = '#c62828' if pct > 20 else ('#ff8f00' if pct > 10 else '#4caf50')
        content += f'''
                    <div style="display:flex;align-items:center;gap:8px">
                        <span style="font-size:.75rem;width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{r['nombre']}">{r['nombre'].split()[0]}</span>
                        <div style="flex:1;background:#f0f0f0;border-radius:4px;height:18px;position:relative">
                            <div style="width:{bar_w}%;background:{bar_c};height:100%;border-radius:4px;transition:width .3s"></div>
                        </div>
                        <span style="font-size:.8rem;font-weight:700;color:{bar_c};min-width:45px;text-align:right">{pct}%</span>
                    </div>'''

    content += f'''
                </div>
            </div>
            <div style="flex:1;min-width:300px">
                <h4 style="font-size:.9rem;color:#666;margin-bottom:.5rem">Resumen General</h4>
                <div style="position:relative;width:180px;height:180px;margin:0 auto">
                    <svg viewBox="0 0 36 36" style="width:100%;height:100%;transform:rotate(-90deg)">
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e0e0e0" stroke-width="3"/>
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="#4caf50" stroke-width="3"
                            stroke-dasharray="{round((total_si/total_citas*100) if total_citas else 0, 1)} 100"/>
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="#c62828" stroke-width="3"
                            stroke-dasharray="{pct_inasis} 100" stroke-dashoffset="-{round((total_si/total_citas*100) if total_citas else 0, 1)}"/>
                    </svg>
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center">
                        <div style="font-size:1.5rem;font-weight:700;color:#c62828">{pct_inasis}%</div>
                        <div style="font-size:.65rem;color:#666">inasistencia</div>
                    </div>
                </div>
                <div style="display:flex;justify-content:center;gap:1.5rem;margin-top:.5rem;font-size:.8rem">
                    <span><span style="display:inline-block;width:10px;height:10px;background:#4caf50;border-radius:50%;margin-right:3px"></span>Asistieron ({total_si})</span>
                    <span><span style="display:inline-block;width:10px;height:10px;background:#c62828;border-radius:50%;margin-right:3px"></span>No asistieron ({total_no})</span>
                </div>
            </div>
        </div>
    </div>

    <div class="card"><h3>🏆 Ranking de Inasistencias por Profesional</h3>
        <p style="font-size:.8rem;color:#666;margin-bottom:.5rem">Ordenado de mayor a menor inasistencia</p>
        <div class="table-wrapper"><table class="citas-table"><thead><tr>
            <th>#</th><th>Profesional</th><th>Especialidad</th><th>Citas</th><th>Asistieron</th><th>No Asistieron</th><th>Pendientes</th><th>Disponibles</th><th>% Inasistencia</th>
        </tr></thead><tbody>{rank_rows}</tbody></table></div></div>

    <div class="card"><h3>📅 Inasistencias por Día</h3>
        <p style="font-size:.8rem;color:#666;margin-bottom:.5rem">Solo días con al menos 1 inasistencia</p>
        <div class="table-wrapper"><table class="citas-table"><thead><tr>
            <th>Día</th><th>Profesional</th><th>Especialidad</th><th>Citas</th><th>No Asistieron</th>
        </tr></thead><tbody>{dia_rows if dia_rows else "<tr><td colspan='5' style='text-align:center;color:#666'>Sin inasistencias registradas</td></tr>"}</tbody></table></div></div>

    <div class="card"><h3>📋 Detalle de Pacientes que No Asistieron</h3>
        <div class="table-wrapper"><table class="citas-table"><thead><tr>
            <th>Fecha</th><th>Hora</th><th>Turno</th><th>Paciente</th><th>DNI</th><th>Celular</th><th>Profesional</th>
        </tr></thead><tbody>{pac_rows if pac_rows else "<tr><td colspan='7' style='text-align:center;color:#666'>Sin inasistencias registradas</td></tr>"}</tbody></table></div></div>'''

    flash_msgs = session.pop('_flashes', [])
    return page('Inasistencias - Sistema de Citas', content, flash_msgs)

@app.route('/exportar_inasistencias')
@login_required
def exportar_inasistencias():
    if session.get('user_rol') == 'lector':
        flash('No tiene permisos para exportar (cuenta de solo lectura)', 'danger')
        return redirect('/')
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    conn = get_db()
    ym = (str(year), f"{month:02d}")

    ranking = conn.execute("""SELECT p.nombre, p.especialidad,
        SUM(CASE WHEN c.estado='Confirmado' THEN 1 ELSE 0 END) as total_citas,
        SUM(CASE WHEN c.asistencia='Asistió' THEN 1 ELSE 0 END) as asistieron,
        SUM(CASE WHEN c.asistencia='No asistió' THEN 1 ELSE 0 END) as no_asistieron,
        SUM(CASE WHEN c.asistencia='Pendiente' AND c.estado='Confirmado' THEN 1 ELSE 0 END) as pendientes
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.turno!='ADMINISTRATIVA' AND c.estado='Confirmado' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA')
        GROUP BY p.id ORDER BY no_asistieron DESC""", ym).fetchall()

    detalle = conn.execute("""SELECT c.fecha, c.hora_inicio, c.turno, c.paciente, c.dni, c.celular,
        p.nombre as prof_nombre, p.especialidad
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=? AND c.asistencia='No asistió' AND c.tipo_paciente NOT IN ('APP','ADMINISTRATIVA')
        ORDER BY c.fecha, p.orden, c.hora_inicio""", ym).fetchall()
    conn.close()

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})

    # Hoja 1: Ranking
    ws1 = wb.add_worksheet('RANKING')
    fmt_h = wb.add_format({'bold': True, 'bg_color': '#c62828', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_size': 10})
    fmt_t = wb.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
    fmt_c = wb.add_format({'border': 1, 'font_size': 10, 'align': 'center'})
    fmt_l = wb.add_format({'border': 1, 'font_size': 10})
    fmt_pct = wb.add_format({'border': 1, 'font_size': 10, 'align': 'center', 'num_format': '0.0%'})
    fmt_red = wb.add_format({'border': 1, 'font_size': 11, 'align': 'center', 'bold': True, 'font_color': '#c62828'})

    ws1.merge_range(0, 0, 0, 7, f'REPORTE DE INASISTENCIAS - {MESES_ES[month].upper()} {year}', fmt_t)
    headers1 = ['#', 'PROFESIONAL', 'ESPECIALIDAD', 'TOTAL CITAS', 'ASISTIERON', 'NO ASISTIERON', 'PENDIENTES', '% INASISTENCIA']
    for i, h in enumerate(headers1): ws1.write(2, i, h, fmt_h)
    for i, r in enumerate(ranking):
        row = i + 3
        no = r['no_asistieron'] or 0; tot = r['total_citas'] or 0
        pct = no / tot if tot else 0
        ws1.write(row, 0, i + 1, fmt_c)
        ws1.write(row, 1, r['nombre'], fmt_l)
        ws1.write(row, 2, r['especialidad'], fmt_c)
        ws1.write(row, 3, tot, fmt_c)
        ws1.write(row, 4, r['asistieron'] or 0, fmt_c)
        ws1.write(row, 5, no, fmt_red)
        ws1.write(row, 6, r['pendientes'] or 0, fmt_c)
        ws1.write(row, 7, pct, fmt_pct)
    ws1.set_column(0, 0, 5); ws1.set_column(1, 1, 40); ws1.set_column(2, 2, 20)
    ws1.set_column(3, 7, 16)

    # Hoja 2: Detalle pacientes
    ws2 = wb.add_worksheet('DETALLE')
    fmt_h2 = wb.add_format({'bold': True, 'bg_color': '#1a365d', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_size': 10})
    ws2.merge_range(0, 0, 0, 6, f'PACIENTES QUE NO ASISTIERON - {MESES_ES[month].upper()} {year}', fmt_t)
    headers2 = ['FECHA', 'HORA', 'TURNO', 'PACIENTE', 'DNI', 'CELULAR', 'PROFESIONAL']
    for i, h in enumerate(headers2): ws2.write(2, i, h, fmt_h2)
    for i, d in enumerate(detalle):
        row = i + 3
        try:
            dt = datetime.strptime(d['fecha'], '%Y-%m-%d')
            fecha_d = f"{DIAS_ES[dt.weekday()]} {dt.day}/{dt.month:02d}"
        except: fecha_d = d['fecha']
        ws2.write(row, 0, fecha_d, fmt_c)
        ws2.write(row, 1, d['hora_inicio'], fmt_c)
        ws2.write(row, 2, d['turno'], fmt_c)
        ws2.write(row, 3, d['paciente'], fmt_l)
        ws2.write(row, 4, d['dni'], fmt_c)
        ws2.write(row, 5, d['celular'], fmt_c)
        ws2.write(row, 6, d['prof_nombre'], fmt_l)
    ws2.set_column(0, 0, 15); ws2.set_column(1, 1, 8); ws2.set_column(2, 2, 10)
    ws2.set_column(3, 3, 35); ws2.set_column(4, 4, 12); ws2.set_column(5, 5, 12); ws2.set_column(6, 6, 35)

    wb.close()
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'inasistencias_{MESES_ES[month]}_{year}.xlsx')

@app.route('/exportar_form')
@login_required
def exportar_form():
    if session.get('user_rol') == 'lector':
        flash('No tiene permisos para exportar (cuenta de solo lectura)', 'danger')
        return redirect('/')
    month_opts = ''.join([f'<option value="{i}" {"selected" if i==datetime.now().month else ""}>{MESES_ES[i]}</option>' for i in range(1, 13)])
    content = f'''<div class="page-header"><h2>📥 Exportar a Excel</h2></div>
    <div class="card">
        <form method="GET" action="/exportar">
            <div class="form-row">
                <div class="form-group"><label>Año</label><input type="number" name="year" value="{datetime.now().year}" class="form-input" min="2024" max="2030"></div>
                <div class="form-group"><label>Mes</label><select name="month" class="form-select">{month_opts}</select></div>
            </div>
            <div class="form-actions"><button type="submit" class="btn btn-success btn-lg">📥 Descargar Excel</button></div>
        </form>
    </div>'''
    flash_msgs = session.pop('_flashes', [])
    return page('Exportar Excel - Sistema de Citas', content, flash_msgs)

@app.route('/exportar')
@login_required
def exportar_excel():
    if session.get('user_rol') == 'lector':
        flash('No tiene permisos para exportar (cuenta de solo lectura)', 'danger')
        return redirect('/')
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    conn = get_db()
    rows = conn.execute("""SELECT c.fecha, c.turno, c.area, p.nombre as profesional,
        c.hora_inicio, c.hora_fin, c.paciente, c.dni, c.edad, c.celular, c.observaciones, c.estado,
        c.tipo_paciente, c.actividad_app, c.asistencia, c.sihce, c.sihce_prof_id, p.color_bg, p.color_font,
        u.nombre as registrado_por, c.creado_en
        FROM citas c JOIN profesionales p ON p.id=c.profesional_id
        LEFT JOIN usuarios u ON u.id=c.creado_por
        WHERE strftime('%Y',c.fecha)=? AND strftime('%m',c.fecha)=?
        ORDER BY c.fecha, CASE c.turno WHEN 'MAÑANA' THEN 1 WHEN 'ADMINISTRATIVA' THEN 2 WHEN 'TARDE' THEN 3 END, CASE p.especialidad WHEN 'PSIQUIATRÍA' THEN 1 WHEN 'PSIQUIATRÍA - LOCACIÓN' THEN 2 WHEN 'MEDICINA' THEN 3 WHEN 'PSICOLOGÍA' THEN 4 WHEN 'TERAPIA DE LENGUAJE' THEN 5 WHEN 'TERAPIA OCUPACIONAL' THEN 6 WHEN 'SIHCE' THEN 7 ELSE 8 END, p.orden, c.hora_inicio""",
        (str(year), f"{month:02d}")).fetchall()
    conn.close()

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('AGENDA')
    fmt_h = wb.add_format({'bold': True, 'bg_color': '#1a365d', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
    fmt_title = wb.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
    fmt_sep = wb.add_format({'bold': True, 'bg_color': '#f1f5f9', 'font_size': 11, 'border': 1, 'align': 'left', 'valign': 'vcenter'})

    # Title
    ws.merge_range(0, 0, 0, 17, f'AGENDA DE CITAS - {MESES_ES[month].upper()} {year}', fmt_title)

    headers = ['FECHA', 'DÍA', 'TURNO', 'ÁREA', 'PROFESIONAL', 'HORA', 'PACIENTE', 'DNI', 'EDAD', 'CELULAR', 'OBSERVACIONES', 'ESTADO', 'TIPO', 'APP', 'ASISTENCIA', 'SIHCE', 'REGISTRADO POR', 'FECHA REGISTRO']
    for i, h in enumerate(headers): ws.write(2, i, h, fmt_h)
    ws.set_column(0, 0, 12); ws.set_column(1, 1, 10); ws.set_column(2, 2, 12); ws.set_column(3, 3, 14)
    ws.set_column(4, 4, 35); ws.set_column(5, 5, 15); ws.set_column(6, 6, 35); ws.set_column(7, 7, 10)
    ws.set_column(8, 8, 6); ws.set_column(9, 9, 12); ws.set_column(10, 10, 25); ws.set_column(11, 12, 14)
    ws.set_column(13, 13, 30); ws.set_column(14, 14, 14); ws.set_column(15, 15, 8); ws.set_column(16, 16, 25); ws.set_column(17, 17, 18)

    fmt_cache = {}
    r = 3
    prev_date = ''; prev_turno = ''
    for row in rows:
        row = dict(row)
        # Separator row when date or turno changes
        curr_date = row['fecha']; curr_turno = row['turno']
        if curr_date != prev_date or (curr_turno != prev_turno and curr_turno in ('MAÑANA','TARDE')):
            if curr_date != prev_date:
                try:
                    dt_sep = datetime.strptime(curr_date, '%Y-%m-%d')
                    sep_text = f"{DIAS_ES[dt_sep.weekday()]} {dt_sep.day} DE {MESES_ES[dt_sep.month].upper()} {dt_sep.year}"
                except: sep_text = curr_date
            if curr_turno in ('MAÑANA','TARDE') and (curr_date != prev_date or curr_turno != prev_turno):
                turno_icon = 'MAÑANA ☀️' if curr_turno == 'MAÑANA' else 'TARDE 🌙'
                if curr_date != prev_date:
                    ws.merge_range(r, 0, r, 17, f"{sep_text} — {turno_icon}", fmt_sep)
                else:
                    ws.merge_range(r, 0, r, 17, f"        {turno_icon}", fmt_sep)
                r += 1
            prev_date = curr_date; prev_turno = curr_turno

        key = (row['color_bg'], row['color_font'])
        if key not in fmt_cache:
            fmt_cache[key] = {
                'c': wb.add_format({'bg_color': key[0], 'font_color': key[1], 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 9}),
                'l': wb.add_format({'bg_color': key[0], 'font_color': key[1], 'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9}),
                'b': wb.add_format({'bg_color': key[0], 'font_color': key[1], 'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 9, 'bold': True}),
            }
        try:
            dt = datetime.strptime(row['fecha'], '%Y-%m-%d')
            fecha_vis = dt.strftime('%d/%m/%Y')
            dia_sem = DIAS_CORTO[dt.weekday()]
        except:
            fecha_vis = row['fecha']; dia_sem = ''
        hora = f"{row['hora_inicio']} - {row['hora_fin']}"
        fc = fmt_cache[key]['c']; fl = fmt_cache[key]['l']; fb = fmt_cache[key]['b']
        ws.write(r, 0, fecha_vis, fc); ws.write(r, 1, dia_sem, fc); ws.write(r, 2, row['turno'], fc)
        ws.write(r, 3, row['area'], fc); ws.write(r, 4, row['profesional'], fb)
        ws.write(r, 5, hora, fc); ws.write(r, 6, row['paciente'], fl)
        ws.write(r, 7, row['dni'], fc); ws.write(r, 8, row.get('edad', ''), fc)
        ws.write(r, 9, row['celular'], fc); ws.write(r, 10, row['observaciones'], fl)
        ws.write(r, 11, row['estado'], fc); ws.write(r, 12, row['tipo_paciente'], fc)
        ws.write(r, 13, row.get('actividad_app', ''), fl)
        ws.write(r, 14, row.get('asistencia', ''), fc)
        ws.write(r, 15, 'SIHCE' if row['sihce'] else '', fc)
        ws.write(r, 16, row.get('registrado_por', '') or '', fl)
        # Fecha de registro (convertir UTC a hora Perú)
        fecha_reg = ''
        if row.get('creado_en'):
            try:
                dt_reg = datetime.strptime(str(row['creado_en'])[:19], '%Y-%m-%d %H:%M:%S') - timedelta(hours=5)
                fecha_reg = dt_reg.strftime('%d/%m/%Y %H:%M')
            except: fecha_reg = ''
        ws.write(r, 17, fecha_reg, fl)
        r += 1

    wb.close(); output.seek(0)
    filename = f"Agenda_{MESES_ES[month]}_{year}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ==============================================================================
# INICIALIZACIÓN
# ==============================================================================
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
