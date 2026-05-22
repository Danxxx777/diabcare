/**
 * navegacion.js — Lógica del sidebar y navegación entre secciones
 */

function mostrarSeccion(nombre, elemento) {
  document.querySelectorAll('.seccion').forEach(s => s.classList.remove('activa'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('activo'));
  document.getElementById('sec-' + nombre).classList.add('activa');
  if (elemento) elemento.classList.add('activo');

  // Cargar datos según la sección
  if (nombre === 'dashboard') cargarEstadisticas();
  if (nombre === 'empresa' || nombre === 'objetivos') cargarEmpresa();
}
