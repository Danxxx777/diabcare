/**
 * empresa.js — Lógica del módulo Empresa y Objetivos
 */

let datosEmpresa = null;

async function cargarEmpresa() {
  if (datosEmpresa) { renderizarEmpresa(); return; }
  try {
    const r = await fetch('/api/empresa');
    datosEmpresa = await r.json();
    renderizarEmpresa();
  } catch (e) { console.error('Error cargando empresa:', e); }
}

function renderizarEmpresa() {
  const d = datosEmpresa;
  if (!d) return;

  // Empresa
  const gridEmpresa = document.getElementById('grid-empresa');
  if (gridEmpresa) {
    gridEmpresa.innerHTML = `
      <div class="tarjeta" style="padding:24px">
        <div class="encabezado-info">
          <div class="icono-info">🎯</div>
          <h3>Misión</h3>
        </div>
        <p>${d.mision}</p>
      </div>
      <div class="tarjeta" style="padding:24px">
        <div class="encabezado-info">
          <div class="icono-info">🔭</div>
          <h3>Visión</h3>
        </div>
        <p>${d.vision}</p>
      </div>`;
  }

  // Objetivos
  const gridObj = document.getElementById('grid-objetivos');
  if (gridObj) {
    const lista = (arr) => arr.map(o => `<li>${o}</li>`).join('');
    gridObj.innerHTML = `
      <div class="tarjeta" style="padding:24px">
        <div class="encabezado-info"><div class="icono-info">📌</div><h3>Estratégicos</h3></div>
        <ul class="lista-obj">${lista(d.objetivos_estrategicos)}</ul>
      </div>
      <div class="tarjeta" style="padding:24px">
        <div class="encabezado-info"><div class="icono-info">🔧</div><h3>Tácticos</h3></div>
        <ul class="lista-obj">${lista(d.objetivos_tacticos)}</ul>
      </div>
      <div class="tarjeta col-completa" style="padding:24px">
        <div class="encabezado-info"><div class="icono-info">⚙️</div><h3>Operacionales</h3></div>
        <ul class="lista-obj">${lista(d.objetivos_operacionales)}</ul>
      </div>`;
  }
}

// Modal de empresa
function abrirModal() {
  document.getElementById('modal-empresa').style.display = 'flex';
  cargarEmpresa();
}

function cerrarModal() {
  document.getElementById('modal-empresa').style.display = 'none';
}

// Cerrar modal al hacer click fuera
document.addEventListener('click', (e) => {
  const modal = document.getElementById('modal-empresa');
  if (modal && e.target === modal) cerrarModal();
});
