/**
 * tablas.js — Lógica del módulo Ver Tablas
 */

async function cargarTabla() {
  const nombre = document.getElementById('selector-tabla').value;
  if (!nombre) return;

  const contenedor = document.getElementById('contenedor-tabla');
  const info = document.getElementById('info-tabla');
  contenedor.innerHTML = '<div class="vacio"><span class="icono">⏳</span>Cargando datos...</div>';
  info.textContent = '';

  try {
    const r = await fetch(`/api/tabla/${nombre}?limit=50`);
    const datos = await r.json();
    const filas = datos.rows;

    if (!filas || filas.length === 0) {
      contenedor.innerHTML = '<div class="vacio"><span class="icono">📭</span>Sin datos disponibles</div>';
      return;
    }

    const columnas = Object.keys(filas[0]);
    info.textContent = `${filas.length} de ${Number(datos.total).toLocaleString('es-EC')} registros · ${columnas.length} columnas`;

    contenedor.innerHTML = `<table>
      <thead><tr>${columnas.map(c => `<th>${c}</th>`).join('')}</tr></thead>
      <tbody>${filas.map(fila =>
        `<tr>${columnas.map(c => `<td title="${fila[c] ?? ''}">${fila[c] ?? '<span style="color:var(--texto3)">—</span>'}</td>`).join('')}</tr>`
      ).join('')}</tbody>
    </table>`;
  } catch (e) {
    contenedor.innerHTML = `<div class="vacio" style="color:var(--rojo)"><span class="icono">⚠️</span>${e.message}</div>`;
  }
}
