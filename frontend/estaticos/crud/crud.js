function cambiarTab(tab) {
  document.querySelectorAll('.crud-tab').forEach(t => t.classList.remove('activo'));
  document.querySelectorAll('.crud-panel').forEach(p => p.classList.remove('activo'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('activo');
  document.getElementById(`panel-${tab}`).classList.add('activo');
  document.querySelectorAll('.alerta-crud').forEach(el => el.innerHTML = '');
}
function mostrarAlerta(id, mensaje, ok) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<div class="alerta-${ok ? 'exito' : 'error'}">${mensaje}</div>`;
  setTimeout(() => el.innerHTML = '', 6000);
}
function mostrarResultado(id, datos) {
  const el = document.getElementById(id);
  if (!el) return;
  const filas = Object.entries(datos).map(([k,v]) => `<tr><td class="col-campo">${k}</td><td class="col-valor">${v}</td></tr>`).join('');
  el.innerHTML = `<div class="resultado-registro"><div class="resultado-titulo">Registro encontrado</div><table class="tabla-resultado"><tbody>${filas}</tbody></table></div>`;
}
async function crearHecho() {
  const campos = {
    year: parseInt(document.getElementById('crear-year').value),
    gender: document.getElementById('crear-gender').value,
    age: parseFloat(document.getElementById('crear-age').value),
    location: document.getElementById('crear-location').value,
    hypertension: parseInt(document.getElementById('crear-hypertension').value),
    heart_disease: parseInt(document.getElementById('crear-heart').value),
    smoking_history: document.getElementById('crear-smoking').value,
    bmi: parseFloat(document.getElementById('crear-bmi').value),
    hbA1c_level: parseFloat(document.getElementById('crear-hba1c').value),
    blood_glucose_level: parseInt(document.getElementById('crear-glucosa').value),
    diabetes: parseInt(document.getElementById('crear-diabetes').value),
  };
  try {
    const r = await fetch('/api/fact', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(campos) });
    const datos = await r.json();
    if (!r.ok) return mostrarAlerta('alerta-crear', datos.detail, false);
    mostrarAlerta('alerta-crear', `Registro creado con ID ${datos.id}`, true);
    document.querySelectorAll('#panel-crear .campo').forEach(c => c.value = '');
  } catch(e) { mostrarAlerta('alerta-crear', e.message, false); }
}
async function leerHecho() {
  const id = document.getElementById('leer-id').value;
  if (id === '') return mostrarAlerta('alerta-leer', 'Ingresa un ID', false);
  document.getElementById('resultado-leer').innerHTML = '<div style="color:var(--texto3);font-size:13px;">Buscando...</div>';
  try {
    const r = await fetch(`/api/fact/${id}`);
    const datos = await r.json();
    if (!r.ok) { document.getElementById('resultado-leer').innerHTML = ''; return mostrarAlerta('alerta-leer', datos.detail, false); }
    mostrarResultado('resultado-leer', datos);
  } catch(e) { document.getElementById('resultado-leer').innerHTML = ''; mostrarAlerta('alerta-leer', e.message, false); }
}
async function actualizarHecho() {
  const id = document.getElementById('act-id').value;
  if (id === '') return mostrarAlerta('alerta-actualizar', 'Ingresa un ID', false);
  const params = new URLSearchParams();
  const imc = document.getElementById('act-bmi').value;
  const hba1c = document.getElementById('act-hba1c').value;
  const glucosa = document.getElementById('act-glucosa').value;
  const diabetes = document.getElementById('act-diabetes').value;
  if (!imc && !hba1c && !glucosa && diabetes === '') return mostrarAlerta('alerta-actualizar', 'Ingresa al menos un campo', false);
  if (imc) params.append('bmi', imc);
  if (hba1c) params.append('hbA1c_level', hba1c);
  if (glucosa) params.append('blood_glucose_level', glucosa);
  if (diabetes !== '') params.append('diabetes', diabetes);
  try {
    const r = await fetch(`/api/fact/${id}?${params}`, { method: 'PUT' });
    const datos = await r.json();
    if (!r.ok) return mostrarAlerta('alerta-actualizar', datos.detail, false);
    mostrarAlerta('alerta-actualizar', `Registro ${id} actualizado`, true);
    mostrarResultado('resultado-actualizar', datos);
  } catch(e) { mostrarAlerta('alerta-actualizar', e.message, false); }
}
async function eliminarHecho() {
  const id = document.getElementById('elim-id').value;
  if (id === '') return mostrarAlerta('alerta-eliminar', 'Ingresa un ID', false);
  if (!confirm(`Eliminar el registro ${id}?`)) return;
  try {
    const r = await fetch(`/api/fact/${id}`, { method: 'DELETE' });
    const datos = await r.json();
    if (!r.ok) return mostrarAlerta('alerta-eliminar', datos.detail, false);
    mostrarAlerta('alerta-eliminar', `Registro ${id} eliminado`, true);
    document.getElementById('elim-id').value = '';
  } catch(e) { mostrarAlerta('alerta-eliminar', e.message, false); }
}
