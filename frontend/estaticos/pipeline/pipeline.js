/**
 * pipeline.js — Lógica del módulo Pipeline ETL
 */

async function recargarDataset() {
  const btn = document.getElementById('btn-recargar');
  const icono = document.getElementById('icono-recargar');
  btn.disabled = true;
  icono.innerHTML = '<span class="spinner"></span>';

  try {
    const r = await fetch('/api/cargar-dataset', { method: 'POST' });
    const datos = await r.json();
    const alerta = document.getElementById('alerta-pipeline');
    alerta.className = 'alerta ' + (r.ok ? 'ok' : 'error');
    alerta.textContent = r.ok
      ? `Dataset recargado: ${datos.registros.toLocaleString('es-EC')} registros`
      : datos.detail;
    alerta.style.display = 'block';
    setTimeout(() => alerta.style.display = 'none', 5000);
  } catch (e) {
    const alerta = document.getElementById('alerta-pipeline');
    alerta.className = 'alerta error';
    alerta.textContent = e.message;
    alerta.style.display = 'block';
  } finally {
    btn.disabled = false;
    icono.textContent = '🔄';
  }
}
