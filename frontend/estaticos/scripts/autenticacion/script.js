// DiabCare Analytics — Script Autenticación
const API = 'http://localhost:8000/api';
let emailRecuperar = '';

// ══ MOSTRAR VISTA ══
function mostrarVista(id) {
  document.querySelectorAll('.vista').forEach(v => v.classList.remove('activa'));
  document.getElementById(id).classList.add('activa');
}

// ══ MOSTRAR ALERTA ══
function mostrarAlerta(idAlerta, mensaje, tipo = 'error') {
  const el = document.getElementById(idAlerta);
  el.textContent = mensaje;
  el.className = `alerta ${tipo}`;
}

function ocultarAlerta(idAlerta) {
  const el = document.getElementById(idAlerta);
  el.className = 'alerta oculto';
}

// ══ TOGGLE PASSWORD ══
function togglePass(inputId, btn) {
  const input = document.getElementById(inputId);
  input.type = input.type === 'password' ? 'text' : 'password';
}

// ══ SPINNER ══
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  const texto = btn.querySelector('.btn-texto');
  const spinner = btn.querySelector('.btn-spinner');
  if (texto) texto.classList.toggle('oculto', loading);
  if (spinner) spinner.classList.toggle('oculto', !loading);
}

// ══ CU01: LOGIN ══
document.getElementById('form-login').addEventListener('submit', async (e) => {
  e.preventDefault();
  ocultarAlerta('alerta-login');
  setLoading('btn-login', true);

  const email = document.getElementById('email-login').value.trim();
  const password = document.getElementById('password-login').value;

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      mostrarAlerta('alerta-login', data.detail || 'Credenciales incorrectas');
      return;
    }

    // Guardar sesión
    localStorage.setItem('dc_token', data.token);
    localStorage.setItem('dc_usuario', JSON.stringify(data.usuario));

    // Redirigir al dashboard
    window.location.href = '/frontend/paginas/dashboard/index.html';

  } catch (err) {
    mostrarAlerta('alerta-login', 'Error de conexión con el servidor');
  } finally {
    setLoading('btn-login', false);
  }
});

// ══ CU03: RECUPERAR CONTRASEÑA ══
document.getElementById('form-recuperar').addEventListener('submit', async (e) => {
  e.preventDefault();
  ocultarAlerta('alerta-recuperar');

  emailRecuperar = document.getElementById('email-recuperar').value.trim();

  try {
    const res = await fetch(`${API}/auth/recuperar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailRecuperar })
    });

    const data = await res.json();

    if (!res.ok) {
      mostrarAlerta('alerta-recuperar', data.detail || 'Error al enviar código');
      return;
    }

    mostrarAlerta('alerta-recuperar', data.mensaje, 'exito');

    // En desarrollo mostramos el código
    if (data.codigo_dev) {
      mostrarAlerta('alerta-recuperar', `Código de prueba: ${data.codigo_dev}`, 'exito');
    }

    setTimeout(() => mostrarVista('vista-codigo'), 1500);

  } catch (err) {
    mostrarAlerta('alerta-recuperar', 'Error de conexión con el servidor');
  }
});

// ══ CU03: VALIDAR CÓDIGO Y RESETEAR ══
document.getElementById('form-codigo').addEventListener('submit', async (e) => {
  e.preventDefault();
  ocultarAlerta('alerta-codigo');

  const codigo = document.getElementById('codigo-reset').value.trim().toUpperCase();
  const passNueva = document.getElementById('pass-nueva').value;
  const passConfirmar = document.getElementById('pass-confirmar').value;

  if (passNueva !== passConfirmar) {
    mostrarAlerta('alerta-codigo', 'Las contraseñas no coinciden');
    return;
  }

  try {
    const res = await fetch(`${API}/auth/resetear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailRecuperar, codigo, password_nueva: passNueva })
    });

    const data = await res.json();

    if (!res.ok) {
      mostrarAlerta('alerta-codigo', data.detail || 'Error al restablecer contraseña');
      return;
    }

    mostrarAlerta('alerta-codigo', 'Contraseña restablecida. Redirigiendo...', 'exito');
    setTimeout(() => mostrarVista('vista-login'), 1500);

  } catch (err) {
    mostrarAlerta('alerta-codigo', 'Error de conexión con el servidor');
  }
});

// ══ VERIFICAR SI YA HAY SESIÓN ACTIVA ══
(function() {
  const token = localStorage.getItem('dc_token');
  if (token) {
    fetch(`${API}/auth/verificar`, {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(res => {
      if (res.ok) window.location.href = '/frontend/paginas/dashboard/index.html';
    }).catch(() => {});
  }
})();