/**
 * dashboard.js — Lógica del módulo Dashboard
 */

const META_ESTADISTICAS = {
  diabetes_dataset:   { etiqueta: 'Dataset Total',   icono: '🗂️' },
  dim_paciente:       { etiqueta: 'Dim. Paciente',    icono: '👤' },
  dim_ubicacion:      { etiqueta: 'Dim. Ubicación',   icono: '📍' },
  dim_raza:           { etiqueta: 'Dim. Raza',        icono: '🌎' },
  dim_condicion:      { etiqueta: 'Dim. Condición',   icono: '🫀' },
  fact_diabetes:      { etiqueta: 'Fact Diabetes',    icono: '🩺', clase: '' },
  total_con_diabetes: { etiqueta: 'Con Diabetes',     icono: '🔴', clase: 'rojo' },
  total_sin_diabetes: { etiqueta: 'Sin Diabetes',     icono: '🟢', clase: 'verde' },
};

async function cargarEstadisticas() {
  const grid = document.getElementById('grid-estadisticas');
  grid.innerHTML = '<div class="tarjeta-stat"><span class="stat-icono">⏳</span><div class="stat-etiqueta">Cargando</div><div class="stat-valor">—</div></div>';

  try {
    const r = await fetch('/api/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const datos = await r.json();

    grid.innerHTML = Object.entries(datos).map(([clave, valor]) => {
      const m = META_ESTADISTICAS[clave] || { etiqueta: clave, icono: '📦', clase: '' };
      return `<div class="tarjeta-stat">
        <span class="stat-icono">${m.icono}</span>
        <div class="stat-etiqueta">${m.etiqueta}</div>
        <div class="stat-valor ${m.clase || ''}">${Number(valor).toLocaleString('es-EC')}</div>
        <div class="stat-clave">${clave}</div>
      </div>`;
    }).join('');
  } catch (e) {
    grid.innerHTML = `<div class="tarjeta-stat">
      <span class="stat-icono">⚠️</span>
      <div class="stat-etiqueta">Error de conexión</div>
      <div class="stat-valor rojo">—</div>
      <div class="stat-clave">Sin conexión al servidor</div>
    </div>`;
  }
}
