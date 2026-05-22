/**
 * logica.js — Lógica del frontend de DiabCare Analytics
 * Consume los endpoints REST del backend FastAPI.
 * Vanilla JS, sin frameworks.
 */

const API = '';

// ── Metadatos de las tarjetas de estadísticas ──────────────────────────────
const META_ESTADISTICAS = {
  diabetes_dataset:   { etiqueta: 'Dataset Total',    icono: '📋', color: '' },
  dim_paciente:       { etiqueta: 'Dim Paciente',      icono: '👤', color: '' },
  dim_ubicacion:      { etiqueta: 'Dim Ubicación',     icono: '📍', color: '' },
  dim_raza:           { etiqueta: 'Dim Raza',          icono: '🌎', color: '' },
  dim_condicion:      { etiqueta: 'Dim Condición',     icono: '🫀', color: '' },
  fact_diabetes:      { etiqueta: 'Fact Diabetes',     icono: '🩺', color: '' },
  total_con_diabetes: { etiqueta: 'Con Diabetes',      icono: '🔴', color: 'rojo' },
  total_sin_diabetes: { etiqueta: 'Sin Diabetes',      icono: '🟢', color: 'verde' },
};

// ── Navegación entre secciones ─────────────────────────────────────────────
function mostrarSeccion(nombre, elemento) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-' + nombre).classList.add('active');
  if (elemento) elemento.classList.add('active');

  // Carga perezosa por sección
  if (nombre === 'dashboard') cargarEstadisticas();
  if (['empresa', 'objetivos'].includes(nombre)) cargarEmpresa();
}

// ── Estadísticas del Dashboard ─────────────────────────────────────────────
async function cargarEstadisticas() {
  try {
    const respuesta = await fetch(API + '/api/stats');
    const datos = await respuesta.json();

    if (!respuesta.ok) {
      throw new Error(datos.detail || 'Error al obtener estadísticas');
    }

    document.getElementById('stats-grid').innerHTML = Object.entries(datos)
      .map(([clave, valor]) => {
        const meta = META_ESTADISTICAS[clave] || { etiqueta: clave, icono: '📦', color: '' };
        return `<div class="stat-card">
          <span class="stat-icon">${meta.icono}</span>
          <div class="stat-label">${meta.etiqueta}</div>
          <div class="stat-value ${meta.color}">${Number(valor).toLocaleString()}</div>
          <div class="stat-sub">${clave}</div>
        </div>`;
      })
      .join('');
  } catch (error) {
    document.getElementById('stats-grid').innerHTML = `
      <div class="stat-card">
        <span class="stat-icon">⚠️</span>
        <div class="stat-label">Error</div>
        <div class="stat-value" style="color:var(--accent3)">—</div>
        <div class="stat-sub">Sin conexión al servidor</div>
      </div>`;
  }
}

// ── Ver Tablas ─────────────────────────────────────────────────────────────
async function cargarTabla() {
  const nombre = document.getElementById('select-tabla').value;
  if (!nombre) return;

  const contenedor = document.getElementById('table-wrapper');
  const info = document.getElementById('table-info');

  contenedor.innerHTML = '<div class="empty-state"><span class="empty-icon">⏳</span>Cargando...</div>';
  info.textContent = '';

  try {
    const respuesta = await fetch(API + `/api/tabla/${nombre}?limit=50`);
    const datos = await respuesta.json();

    if (!respuesta.ok) {
      contenedor.innerHTML = `<div class="empty-state" style="color:var(--accent3)">
        <span class="empty-icon">⚠️</span>${datos.detail || 'Error al cargar la tabla'}
      </div>`;
      return;
    }

    const filas = datos.rows;

    if (!filas || filas.length === 0) {
      contenedor.innerHTML = '<div class="empty-state"><span class="empty-icon">📭</span>Sin datos disponibles</div>';
      return;
    }

    const columnas = Object.keys(filas[0]);
    info.textContent = `${filas.length} de ${Number(datos.total).toLocaleString()} registros · ${columnas.length} columnas`;

    contenedor.innerHTML = `
      <table>
        <thead>
          <tr>${columnas.map(c => `<th>${c}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${filas.map(fila =>
            `<tr>${columnas.map(c =>
              `<td title="${fila[c] ?? ''}">${fila[c] ?? '<span style="color:var(--text3)">null</span>'}</td>`
            ).join('')}</tr>`
          ).join('')}
        </tbody>
      </table>`;
  } catch (error) {
    contenedor.innerHTML = `<div class="empty-state" style="color:var(--accent3)">
      <span class="empty-icon">⚠️</span>${error.message}
    </div>`;
  }
}

// ── CRUD fact_diabetes ─────────────────────────────────────────────────────

/**
 * Muestra una alerta temporal en el elemento indicado.
 * @param {string} idElemento - ID del elemento de alerta en el DOM.
 * @param {string} mensaje - Texto a mostrar.
 * @param {boolean} exito - true para estilo verde, false para rojo.
 */
function mostrarAlerta(idElemento, mensaje, exito) {
  const elemento = document.getElementById(idElemento);
  elemento.className = 'alert ' + (exito ? 'ok' : 'err');
  elemento.textContent = mensaje;
  elemento.style.display = 'block';
  setTimeout(() => { elemento.style.display = 'none'; }, 5000);
}

async function crudLeer() {
  const id = document.getElementById('read-id').value;
  if (id === '') return mostrarAlerta('read-result', 'Ingresa un ID', false);

  try {
    const respuesta = await fetch(API + `/api/fact/${id}`);
    const datos = await respuesta.json();
    if (!respuesta.ok) return mostrarAlerta('read-result', datos.detail, false);
    mostrarAlerta(
      'read-result',
      `BMI: ${datos.bmi} | hbA1c: ${datos.hbA1c_level} | Glucosa: ${datos.blood_glucose_level} | Diabetes: ${datos.diabetes}`,
      true,
    );
  } catch (error) {
    mostrarAlerta('read-result', error.message, false);
  }
}

async function crudActualizar() {
  const id = document.getElementById('upd-id').value;
  if (id === '') return mostrarAlerta('upd-result', 'Ingresa un ID', false);

  const params = new URLSearchParams();
  const bmi      = document.getElementById('upd-bmi').value;
  const hba1c    = document.getElementById('upd-hba1c').value;
  const glucosa  = document.getElementById('upd-glucose').value;
  const diabetes = document.getElementById('upd-diabetes').value;

  if (bmi)      params.append('bmi', bmi);
  if (hba1c)    params.append('hbA1c_level', hba1c);
  if (glucosa)  params.append('blood_glucose_level', glucosa);
  if (diabetes !== '') params.append('diabetes', diabetes);

  try {
    const respuesta = await fetch(API + `/api/fact/${id}?${params}`, { method: 'PUT' });
    const datos = await respuesta.json();
    if (!respuesta.ok) return mostrarAlerta('upd-result', datos.detail, false);
    mostrarAlerta('upd-result', `✅ Registro ${id} actualizado correctamente`, true);
  } catch (error) {
    mostrarAlerta('upd-result', error.message, false);
  }
}

async function crudEliminar() {
  const id = document.getElementById('del-id').value;
  if (id === '') return mostrarAlerta('del-result', 'Ingresa un ID', false);
  if (!confirm(`¿Eliminar el registro ${id}? Esta acción no se puede deshacer.`)) return;

  try {
    const respuesta = await fetch(API + `/api/fact/${id}`, { method: 'DELETE' });
    const datos = await respuesta.json();
    if (!respuesta.ok) return mostrarAlerta('del-result', datos.detail, false);
    mostrarAlerta(
      'del-result',
      `✅ Registro eliminado. Quedan ${datos.registros_restantes.toLocaleString()} registros`,
      true,
    );
  } catch (error) {
    mostrarAlerta('del-result', error.message, false);
  }
}

// ── Recarga del dataset desde MinIO ───────────────────────────────────────
async function recargarDataset() {
  const boton = document.getElementById('btn-reload');
  const icono = document.getElementById('reload-icon');

  boton.disabled = true;
  icono.innerHTML = '<span class="spinner"></span>';

  try {
    const respuesta = await fetch(API + '/api/cargar-dataset', { method: 'POST' });
    const datos = await respuesta.json();

    if (respuesta.ok) {
      mostrarAlerta(
        'reload-result',
        `✅ Dataset recargado: ${datos.registros.toLocaleString()} registros`,
        true,
      );
    } else {
      mostrarAlerta('reload-result', datos.detail || 'Error al recargar', false);
    }
  } catch (error) {
    mostrarAlerta('reload-result', error.message, false);
  } finally {
    boton.disabled = false;
    icono.textContent = '🔄';
  }
}

// ── Información corporativa ────────────────────────────────────────────────
let datosEmpresa = null;

async function cargarEmpresa() {
  // Reutilizar caché si ya se cargó
  if (datosEmpresa) {
    renderizarEmpresa();
    return;
  }

  try {
    const respuesta = await fetch(API + '/api/empresa');
    datosEmpresa = await respuesta.json();
    renderizarEmpresa();
  } catch (error) {
    console.error('Error al cargar datos de empresa:', error);
  }
}

function renderizarEmpresa() {
  const d = datosEmpresa;
  if (!d) return;

  // Sección Empresa: misión y visión
  const gridEmpresa = document.getElementById('empresa-grid');
  if (gridEmpresa) {
    gridEmpresa.innerHTML = `
      <div class="info-card">
        <div class="info-card-header"><div class="info-card-icon">🎯</div><h3>Misión</h3></div>
        <p>${d.mision}</p>
      </div>
      <div class="info-card">
        <div class="info-card-header"><div class="info-card-icon">🔭</div><h3>Visión</h3></div>
        <p>${d.vision}</p>
      </div>`;
  }

  // Sección Objetivos: estratégicos, tácticos y operacionales
  const gridObjetivos = document.getElementById('obj-grid');
  if (gridObjetivos) {
    gridObjetivos.innerHTML = `
      <div class="info-card">
        <div class="info-card-header"><div class="info-card-icon">📌</div><h3>Estratégicos</h3></div>
        <ul class="obj-list">${d.objetivos_estrategicos.map(o => `<li>${o}</li>`).join('')}</ul>
      </div>
      <div class="info-card">
        <div class="info-card-header"><div class="info-card-icon">🔧</div><h3>Tácticos</h3></div>
        <ul class="obj-list">${d.objetivos_tacticos.map(o => `<li>${o}</li>`).join('')}</ul>
      </div>
      <div class="info-card full">
        <div class="info-card-header"><div class="info-card-icon">⚙️</div><h3>Operacionales</h3></div>
        <ul class="obj-list">${d.objetivos_operacionales.map(o => `<li>${o}</li>`).join('')}</ul>
      </div>`;
  }
}

// ── Inicialización ─────────────────────────────────────────────────────────
cargarEstadisticas();
