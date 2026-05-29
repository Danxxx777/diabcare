// DiabCare Analytics — Script Usuarios (P2)
const API = 'http://localhost:8000/api';
let usuarioEditando = null;
let accionConfirmar = null;

// ══ AUTH ══
function obtenerToken() {
  const token = localStorage.getItem('dc_token');
  if (!token) { window.location.href = '/frontend/paginas/autenticacion/index.html'; return null; }
  return token;
}

function cerrarSesion() {
  localStorage.removeItem('dc_token');
  localStorage.removeItem('dc_usuario');
  window.location.href = '/frontend/paginas/autenticacion/index.html';
}

function mostrarAlertaPage(msg, tipo = 'error') {
  const el = document.getElementById('alerta-page');
  el.textContent = msg;
  el.className = `alerta ${tipo}`;
  setTimeout(() => el.className = 'alerta oculto', 4000);
}

// ══ CARGAR USUARIOS ══
async function cargarUsuarios() {
  const token = obtenerToken();
  if (!token) return;

  try {
    const res = await fetch(`${API}/usuarios/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.status === 401) { cerrarSesion(); return; }
    const usuarios = await res.json();
    renderTabla(usuarios);
  } catch {
    mostrarAlertaPage('Error al cargar usuarios');
  }
}

function renderTabla(usuarios) {
  document.getElementById('total-usuarios').textContent = `${usuarios.length} usuario${usuarios.length !== 1 ? 's' : ''}`;
  const tbody = document.getElementById('tbody-usuarios');

  if (!usuarios.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="tabla-vacia">No hay usuarios registrados</td></tr>';
    return;
  }

  tbody.innerHTML = usuarios.map(u => `
    <tr>
      <td><strong>${u.nombre}</strong></td>
      <td>${u.email}</td>
      <td>${badgeRol(u.id_rol)}</td>
      <td>${u.activo ? '<span class="badge badge-activo">Activo</span>' : '<span class="badge badge-inactivo">Inactivo</span>'}</td>
      <td>${formatFecha(u.creado_en)}</td>
      <td>
        <div class="acciones">
          <button class="btn-accion btn-editar" onclick="abrirModal('editar', ${JSON.stringify(u).replace(/"/g, '&quot;')})">Editar</button>
          <button class="btn-accion btn-rol" onclick="abrirModal('rol', ${JSON.stringify(u).replace(/"/g, '&quot;')})">Rol</button>
          ${u.activo
            ? `<button class="btn-accion btn-desactivar" onclick="confirmarDesactivar('${u.id}', '${u.nombre}')">Desactivar</button>`
            : `<button class="btn-accion btn-reactivar" onclick="confirmarReactivar('${u.id}', '${u.nombre}')">Reactivar</button>`
          }
        </div>
      </td>
    </tr>
  `).join('');
}

function badgeRol(rol) {
  const clases = { administrador: 'badge-admin', medico: 'badge-medico', analista: 'badge-analista' };
  return `<span class="badge ${clases[rol] || ''}">${rol}</span>`;
}

function formatFecha(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ══ MODAL CREAR/EDITAR ══
function abrirModal(modo, usuario = null) {
  usuarioEditando = usuario;
  document.getElementById('alerta-modal').className = 'alerta oculto';
  document.getElementById('form-usuario').reset();
  document.getElementById('usuario-id').value = '';

  const titulo = document.getElementById('modal-titulo');
  const campoPwd = document.getElementById('campo-password');
  const inputPwd = document.getElementById('usuario-password');

  if (modo === 'crear') {
    titulo.textContent = 'Nuevo usuario';
    campoPwd.style.display = 'block';
    inputPwd.required = true;
  } else if (modo === 'editar') {
    titulo.textContent = 'Editar usuario';
    campoPwd.style.display = 'none';
    inputPwd.required = false;
    document.getElementById('usuario-id').value = usuario.id;
    document.getElementById('usuario-nombre').value = usuario.nombre;
    document.getElementById('usuario-email').value = usuario.email;
    document.getElementById('usuario-rol').value = usuario.id_rol;
  } else if (modo === 'rol') {
    titulo.textContent = 'Asignar rol';
    campoPwd.style.display = 'none';
    inputPwd.required = false;
    document.getElementById('usuario-id').value = usuario.id;
    document.getElementById('usuario-nombre').value = usuario.nombre;
    document.getElementById('usuario-nombre').disabled = true;
    document.getElementById('usuario-email').value = usuario.email;
    document.getElementById('usuario-email').disabled = true;
    document.getElementById('usuario-rol').value = usuario.id_rol;
  }

  document.getElementById('modal-usuario').classList.remove('oculto');
}

function cerrarModal() {
  document.getElementById('modal-usuario').classList.add('oculto');
  document.getElementById('usuario-nombre').disabled = false;
  document.getElementById('usuario-email').disabled = false;
  usuarioEditando = null;
}

// ══ GUARDAR USUARIO ══
document.getElementById('form-usuario').addEventListener('submit', async (e) => {
  e.preventDefault();
  const token = obtenerToken();
  if (!token) return;

  const id = document.getElementById('usuario-id').value;
  const nombre = document.getElementById('usuario-nombre').value.trim();
  const email = document.getElementById('usuario-email').value.trim();
  const password = document.getElementById('usuario-password').value;
  const id_rol = document.getElementById('usuario-rol').value;

  document.getElementById('alerta-modal').className = 'alerta oculto';

  try {
    let res, body;

    if (!id) {
      // CU05: Crear
      body = { nombre, email, password, id_rol };
      res = await fetch(`${API}/usuarios/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body)
      });
    } else if (usuarioEditando) {
      // CU08: Solo rol
      if (document.getElementById('usuario-nombre').disabled) {
        res = await fetch(`${API}/usuarios/${id}/rol`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ id_rol })
        });
      } else {
        // CU06: Editar
        body = { nombre, email, id_rol };
        res = await fetch(`${API}/usuarios/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(body)
        });
      }
    }

    const data = await res.json();
    if (!res.ok) {
      const el = document.getElementById('alerta-modal');
      el.textContent = data.detail || 'Error al guardar';
      el.className = 'alerta error';
      return;
    }

    cerrarModal();
    mostrarAlertaPage(data.mensaje || 'Guardado correctamente', 'exito');
    cargarUsuarios();

  } catch {
    const el = document.getElementById('alerta-modal');
    el.textContent = 'Error de conexión';
    el.className = 'alerta error';
  }
});

// ══ CONFIRMAR DESACTIVAR/REACTIVAR ══
function confirmarDesactivar(id, nombre) {
  document.getElementById('confirmar-texto').textContent = `¿Desactivar al usuario "${nombre}"? No podrá iniciar sesión.`;
  accionConfirmar = async () => {
    const token = obtenerToken();
    const res = await fetch(`${API}/usuarios/${id}/desactivar`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    cerrarConfirmar();
    mostrarAlertaPage(res.ok ? data.mensaje : data.detail, res.ok ? 'exito' : 'error');
    if (res.ok) cargarUsuarios();
  };
  document.getElementById('modal-confirmar').classList.remove('oculto');
  document.getElementById('btn-confirmar').onclick = accionConfirmar;
}

function confirmarReactivar(id, nombre) {
  document.getElementById('confirmar-texto').textContent = `¿Reactivar al usuario "${nombre}"?`;
  accionConfirmar = async () => {
    const token = obtenerToken();
    const res = await fetch(`${API}/usuarios/${id}/reactivar`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    cerrarConfirmar();
    mostrarAlertaPage(res.ok ? data.mensaje : data.detail, res.ok ? 'exito' : 'error');
    if (res.ok) cargarUsuarios();
  };
  document.getElementById('modal-confirmar').classList.remove('oculto');
  document.getElementById('btn-confirmar').onclick = accionConfirmar;
}

function cerrarConfirmar() {
  document.getElementById('modal-confirmar').classList.add('oculto');
}

// ══ INIT ══
(function() {
  const token = obtenerToken();
  if (!token) return;
  const usuario = JSON.parse(localStorage.getItem('dc_usuario') || '{}');
  document.getElementById('sidebar-usuario').textContent = usuario.nombre || '';
  if (usuario.rol !== 'administrador') {
    window.location.href = '/frontend/paginas/dashboard/index.html';
    return;
  }
  cargarUsuarios();
})();