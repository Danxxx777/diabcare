/**
 * DiabCare Hospital - navegación por departamentos y roles.
 * Matriz de acceso por rol (admin = supervisión total).
 */
window.DiabCareNav = {
  getApi() {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    const { protocol, hostname, port, origin } = window.location;
    if (port === '8000') return origin;
    const host = hostname && hostname !== '' ? hostname : 'localhost';
    return `${protocol}//${host}:8000`;
  },
  get API() { return this.getApi(); },

  /** Home por rol cuando no hay permiso en la página actual */
  HOME_POR_ROL: {
    administrador: '/paginas/seguridad/usuarios/index.html',
    medico: '/paginas/clinico/mis_citas/index.html',
    enfermero: '/paginas/clinico/pacientes/index.html',
    farmaceutico: '/paginas/negocio/farmacia/index.html',
    analista: '/paginas/clinico/analisis/diabetes/index.html',
  },

  MODULOS_NAVEGABLES: [
    'pacientes', 'admisiones', 'citas', 'mis_citas', 'registros', 'comorbilidades',
    'laboratorio', 'urgencias',
    'recetas', 'farmacia', 'facturacion', 'rrhh',
    'analisis', 'prediccion', 'reportes',
    'dataset', 'pipeline', 'modelo',
    'usuarios', 'auditoria', 'configuracion', 'notificaciones',
  ],

  MODULOS_PROXIMO: [],

  CATEGORIAS: [
    {
      id: 'atencion',
      label: 'Atención clínica',
      items: [
        { modulo: 'pacientes', label: 'Pacientes / HCE', subs: [
          { href: '/paginas/clinico/pacientes/index.html', label: 'Expedientes' },
        ]},
        { modulo: 'admisiones', label: 'Admisiones', subs: [
          { href: '/paginas/clinico/admisiones/index.html', label: 'Ingresos' },
        ]},
        { modulo: 'citas', label: 'Recepción / turnos', subs: [
          { href: '/paginas/clinico/agenda/index.html', label: 'Agenda y cobro consulta' },
        ]},
        { modulo: 'mis_citas', label: 'Mis citas', subs: [
          { href: '/paginas/clinico/mis_citas/index.html', label: 'Turnos del médico' },
        ]},
        { modulo: 'registros', label: 'Registro clínico', subs: [
          { href: '/paginas/clinico/registros_clinicos/index.html', label: 'Consultas por paciente' },
        ]},
        { modulo: 'comorbilidades', label: 'Comorbilidades', subs: [
          { href: '/paginas/clinico/comorbilidades/index.html', label: 'Complicaciones' },
        ]},
        { modulo: 'laboratorio', label: 'Laboratorio', subs: [
          { href: '/paginas/clinico/laboratorio/index.html', label: 'Órdenes y resultados' },
        ]},
        { modulo: 'urgencias', label: 'Urgencias', subs: [
          { href: '/paginas/clinico/urgencias/index.html', label: 'Triage y atención' },
        ]},
      ],
    },
    {
      id: 'farmacia_rx',
      label: 'Farmacia y recetas',
      items: [
        { modulo: 'recetas', label: 'Recetas médicas', subs: [
          { href: '/paginas/negocio/recetas/index.html', label: 'Prescribir (médico)' },
        ]},
        { modulo: 'farmacia', label: 'Farmacia', subs: [
          { href: '/paginas/negocio/farmacia/index.html', label: 'Mostrador e inventario' },
        ]},
      ],
    },
    {
      id: 'negocio',
      label: 'Negocio hospitalario',
      items: [
        { modulo: 'facturacion', label: 'Caja / facturación', subs: [
          { href: '/paginas/negocio/facturacion/index.html', label: 'Caja y facturación' },
        ]},
        { modulo: 'rrhh', label: 'RRHH / costeo', subs: [
          { href: '/paginas/negocio/rrhh/index.html', label: 'Personal y turnos' },
        ]},
      ],
    },
    {
      id: 'inteligencia',
      label: 'Análisis y decisión',
      items: [
        { modulo: 'analisis', label: 'Dashboard / BI', subs: [
          { href: '/paginas/clinico/analisis/diabetes/index.html', label: 'Calidad diabetes' },
          { href: '/paginas/clinico/analisis/index.html', label: 'Dashboard ejecutivo' },
          { href: '/paginas/clinico/analisis/estadisticas/index.html', label: 'Estadísticas clínicas' },
        ]},
        { modulo: 'prediccion', label: 'Predicción ML', subs: [
          { href: '/paginas/clinico/prediccion/index.html', label: 'Inferencia clínica' },
        ]},
        { modulo: 'reportes', label: 'Reportes PDF', subs: [
          { href: '/paginas/clinico/reportes/index.html', label: 'Generar y descargar' },
        ]},
      ],
    },
    {
      id: 'datos',
      label: 'Datos e ingeniería',
      items: [
        { modulo: 'dataset', label: 'Dataset / DWH', subs: [
          { href: '/paginas/datos/dataset/index.html', label: 'Hechos y dimensiones' },
          { href: '/paginas/datos/dataset/generador.html', label: 'Generador sintético' },
        ]},
        { modulo: 'pipeline', label: 'Pipeline ELT', subs: [
          { href: '/paginas/datos/pipeline_elt/index.html', label: 'Estado del pipeline' },
        ]},
        { modulo: 'modelo', label: 'Modelo ML', subs: [
          { href: '/paginas/datos/modelo_ml/index.html', label: 'Entrenamiento' },
        ]},
      ],
    },
    {
      id: 'gobierno',
      label: 'Gobierno y acceso',
      items: [
        { modulo: 'usuarios', label: 'Usuarios y roles', subs: [
          { href: '/paginas/seguridad/usuarios/index.html', label: 'Cuentas' },
        ]},
        { modulo: 'notificaciones', label: 'Notificaciones', subs: [
          { href: '/paginas/notificaciones/index.html', label: 'Alertas y correo' },
        ]},
        { modulo: 'auditoria', label: 'Auditoría', subs: [
          { href: '/paginas/gobierno/auditoria/index.html', label: 'Eventos' },
        ]},
        { modulo: 'configuracion', label: 'Configuración', subs: [
          { href: '/paginas/gobierno/configuracion/index.html', label: 'Parámetros' },
        ]},
      ],
    },
  ],

  get PRESENTACION() {
    return this.MODULOS_NAVEGABLES.slice();
  },

  _esProximo(item) {
    return item.pronto === true || this.MODULOS_PROXIMO.includes(item.modulo);
  },

  /**
   * Quién ve qué en el menú.
   * Administrador (app): TODO — supervisión y demos; no es el operador diario.
   * Farmacéutico: admin. clínica (recepción, ingresos, farmacia, facturación).
   * Enfermería: apoyo recepción / lab / urgencias.
   * Médico: consulta + documentación.
   * Analista: BI, datos, consulta facturación/RRHH.
   */
  ACCESO: {
    administrador: [
      'pacientes', 'admisiones', 'citas', 'mis_citas', 'registros', 'comorbilidades',
      'laboratorio', 'urgencias', 'recetas', 'farmacia', 'facturacion', 'rrhh',
      'analisis', 'prediccion', 'reportes',
      'dataset', 'pipeline', 'modelo',
      'usuarios', 'notificaciones', 'auditoria', 'configuracion',
    ],
    medico: [
      'pacientes', 'mis_citas', 'registros', 'comorbilidades',
      'laboratorio', 'urgencias', 'recetas',
      'analisis', 'prediccion', 'reportes', 'notificaciones',
    ],
    enfermero: [
      'pacientes', 'admisiones', 'citas', 'laboratorio', 'urgencias', 'notificaciones',
    ],
    farmaceutico: [
      'pacientes', 'admisiones', 'citas', 'urgencias',
      'farmacia', 'facturacion',
      'analisis', 'reportes', 'notificaciones',
    ],
    analista: [
      'analisis', 'prediccion', 'reportes',
      'facturacion', 'rrhh',
      'dataset', 'pipeline', 'modelo', 'notificaciones',
    ],
  },

  _moduloDesdeRuta(href) {
    const mapa = [
      ['/paginas/clinico/pacientes/', 'pacientes'],
      ['/paginas/clinico/admisiones/', 'admisiones'],
      ['/paginas/clinico/agenda/', 'citas'],
      ['/paginas/clinico/mis_citas/', 'mis_citas'],
      ['/paginas/clinico/registros_clinicos/', 'registros'],
      ['/paginas/clinico/comorbilidades/', 'comorbilidades'],
      ['/paginas/clinico/laboratorio/', 'laboratorio'],
      ['/paginas/clinico/urgencias/', 'urgencias'],
      ['/paginas/clinico/analisis/', 'analisis'],
      ['/paginas/clinico/prediccion/', 'prediccion'],
      ['/paginas/clinico/reportes/', 'reportes'],
      ['/paginas/negocio/facturacion/', 'facturacion'],
      ['/paginas/negocio/farmacia/', 'farmacia'],
      ['/paginas/negocio/recetas/', 'recetas'],
      ['/paginas/negocio/rrhh/', 'rrhh'],
      ['/paginas/datos/dataset/', 'dataset'],
      ['/paginas/datos/pipeline_elt/', 'pipeline'],
      ['/paginas/datos/modelo_ml/', 'modelo'],
      ['/paginas/seguridad/usuarios/', 'usuarios'],
      ['/paginas/seguridad/perfil/', 'usuarios'],
      ['/paginas/gobierno/auditoria/', 'auditoria'],
      ['/paginas/gobierno/configuracion/', 'configuracion'],
      ['/paginas/notificaciones/', 'notificaciones'],
    ];
    for (const [prefijo, modulo] of mapa) {
      if (href.includes(prefijo)) return modulo;
    }
    return null;
  },

  _categoriaActiva(activeHref) {
    const mod = this._moduloDesdeRuta(activeHref);
    if (!mod) return this.CATEGORIAS[0]?.id || null;
    for (const cat of this.CATEGORIAS) {
      if (cat.items.some(it => it.modulo === mod)) return cat.id;
    }
    return null;
  },

  _itemHtml(item, activeHref) {
    const proximo = this._esProximo(item);
    const subs = item.subs || [];

    if (subs.length === 1) {
      const sub = subs[0];
      const active = activeHref === sub.href || activeHref.endsWith(sub.href);
      const badge = proximo ? '<span class="nav-badge">próximo</span>' : '';
      return `<a class="nav-group-link${active ? ' active' : ''}${proximo ? ' nav-link-proximo' : ''}" href="${sub.href}" data-modulo="${item.modulo}"${proximo ? ' data-proximo="1"' : ''}>
        <span class="nav-group-icon">${DiabCareIcons.nav(item.modulo)}</span>
        <span class="nav-group-label">${item.label}</span>${badge}
      </a>`;
    }

    const isActiveGroup = subs.some(s =>
      activeHref.startsWith(s.href.replace(/\.html$/, '')));
    let html = `<div class="nav-group${proximo ? ' nav-group-proximo' : ''}" data-modulo="${item.modulo}"${proximo ? ' data-proximo="1"' : ''}>`;
    html += `<div class="nav-group-header${isActiveGroup ? ' open' : ''}" onclick="DiabCareNav.toggleModulo(this)">`;
    html += `<span class="nav-group-icon">${DiabCareIcons.nav(item.modulo)}</span>`;
    html += `<span class="nav-group-label">${item.label}</span>`;
    if (proximo) html += '<span class="nav-badge">próximo</span>';
    html += `<span class="nav-chevron">${DiabCareIcons.svg('chevron', 12)}</span></div>`;
    html += `<div class="nav-sub${isActiveGroup ? ' open' : ''}">`;
    for (const sub of subs) {
      const active = activeHref === sub.href || activeHref.endsWith(sub.href);
      html += `<a class="nav-sub-item${active ? ' active' : ''}" href="${sub.href}">`;
      html += `<div class="nav-dot"></div><span class="nav-sub-label">${sub.label}</span></a>`;
    }
    html += '</div></div>';
    return html;
  },

  init(activeHref) {
    const href = activeHref || window.location.pathname;
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const enAuth = href.includes('/seguridad/autenticacion') || href === '/' || href === '/index.html';
    const enPerfil = href.includes('/seguridad/perfil');
    if (u.debe_cambiar_password && !enAuth && !enPerfil) {
      window.location.href = '/paginas/seguridad/perfil/index.html?forzar=1';
      return;
    }
    this.render(href);
    this.initUser();
    this.aplicarRoles();
    if (typeof DiabCareAPI !== 'undefined') {
      DiabCareAPI.actualizarEstadoTopbar();
    }
  },

  render(activeHref) {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;

    let navHtml = '';
    const catActiva = this._categoriaActiva(activeHref);
    for (const cat of this.CATEGORIAS) {
      const abierta = cat.id === catActiva;
      navHtml += `<div class="nav-cat-block" data-categoria="${cat.id}">`;
      navHtml += `<button type="button" class="nav-cat-header${abierta ? ' open' : ''}" onclick="DiabCareNav.toggleCategoria(this)" aria-expanded="${abierta}">`;
      navHtml += `<span class="nav-cat-label">${cat.label}</span>`;
      navHtml += `<span class="nav-chevron">${DiabCareIcons.svg('chevron', 12)}</span>`;
      navHtml += `</button>`;
      navHtml += `<div class="nav-categoria${abierta ? ' open' : ''}">`;
      for (const item of cat.items) {
        navHtml += this._itemHtml(item, activeHref);
      }
      navHtml += '</div></div>';
    }

    mount.innerHTML = `
      <div class="logo-area">
        <img class="logo-mark" src="/estaticos/img/logo-icon.svg" alt="DiabCare" width="28" height="28">
        <div><div class="logo-text">DiabCare</div><div class="logo-sub">Hospital</div></div>
      </div>
      <nav class="nav">${navHtml}</nav>
      <div class="sidebar-bottom">
        <div class="user-row-wrap">
          <button type="button" class="user-row user-row-btn" onclick="DiabCareNav.irPerfil()" title="Mi perfil">
            <div class="user-avatar" id="userAvatar">A</div>
            <div class="user-info">
              <div class="user-name" id="userName">Cargando...</div>
              <div class="user-rol" id="userRol">-</div>
            </div>
            <span class="user-perfil-hint">${DiabCareIcons.svg('chevron', 12)}</span>
          </button>
          <button type="button" class="btn-logout" onclick="DiabCareNav.cerrarSesion()" title="Cerrar sesión">${DiabCareIcons.svg('logout', 14)}</button>
        </div>
      </div>`;
  },

  toggleCategoria(btn) {
    btn.classList.toggle('open');
    const panel = btn.nextElementSibling;
    if (panel) panel.classList.toggle('open');
    btn.setAttribute('aria-expanded', btn.classList.contains('open') ? 'true' : 'false');
  },

  toggleModulo(h) {
    h.classList.toggle('open');
    const s = h.nextElementSibling;
    if (s) s.classList.toggle('open');
  },

  toggle(h) { this.toggleModulo(h); },

  initUser() {
    const t = localStorage.getItem('token');
    if (!t) {
      this.forzarCierreSesion();
      return;
    }
    if (this.tokenExpirado(t)) {
      this.forzarCierreSesion('Tu sesión expiró. Inicia sesión de nuevo.');
      return;
    }
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const nameEl = document.getElementById('userName');
    if (nameEl && u.nombre) {
      nameEl.textContent = u.nombre;
      const rolEl = document.getElementById('userRol');
      if (rolEl) rolEl.textContent = this.etiquetaRol(u.rol);
    }
    this.pintarAvatarSidebar(u);
  },

  pintarAvatarSidebar(u) {
    const av = document.getElementById('userAvatar');
    if (!av) return;
    const nombre = (u && u.nombre) || 'U';
    const letra = (nombre[0] || 'U').toUpperCase();
    const token = localStorage.getItem('token') || '';
    if (!token) {
      av.textContent = letra;
      return;
    }
    av.textContent = letra;
    const api = this.getApi();
    const bust = (u && u.foto_bust) || Date.now();
    fetch(`${api}/api/auth/perfil/foto?t=${bust}`, {
      headers: { Authorization: 'Bearer ' + token },
    })
      .then(r => (r.ok ? r.blob() : Promise.reject()))
      .then(b => {
        if (!b || !b.type || !b.type.startsWith('image/')) throw new Error('no image');
        const url = URL.createObjectURL(b);
        av.innerHTML = '';
        const img = document.createElement('img');
        img.alt = nombre;
        img.src = url;
        av.appendChild(img);
        try {
          const cur = JSON.parse(localStorage.getItem('usuario') || '{}');
          cur.tiene_foto = true;
          localStorage.setItem('usuario', JSON.stringify(cur));
        } catch (_) {}
      })
      .catch(() => {
        av.textContent = letra;
      });
  },

  etiquetaRol(rol) {
    const map = {
      administrador: 'Admin de sistema',
      medico: 'Médico',
      enfermero: 'Enfermero',
      farmaceutico: 'Farmacéutico (clínica)',
      analista: 'Analista',
    };
    return map[rol] || rol || '-';
  },

  aplicarRoles() {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const rol = u.rol || '';
    const permitidos = this.ACCESO[rol];
    if (!permitidos) return;

    document.querySelectorAll('[data-modulo]').forEach(el => {
      const mod = el.dataset.modulo;
      el.style.display = permitidos.includes(mod) ? '' : 'none';
    });

    document.querySelectorAll('.nav-cat-block[data-categoria]').forEach(block => {
      const items = block.querySelectorAll('[data-modulo]');
      const visibles = [...items].some(el => el.style.display !== 'none');
      block.style.display = visibles ? '' : 'none';
    });
  },

  async cerrarSesion() {
    const t = localStorage.getItem('token');
    try {
      if (t) {
        const ctrl = new AbortController();
        const to = setTimeout(() => ctrl.abort(), 2500);
        try {
          await fetch(`${this.getApi()}/api/auth/logout`, {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + t },
            signal: ctrl.signal,
          });
        } finally {
          clearTimeout(to);
        }
      }
    } catch (_) { /* ignore: token ya inválido o red */ }
    sessionStorage.setItem('logout', '1');
    localStorage.clear();
    window.location.href = '/';
  },

  /** JWT exp (segundos) → true si ya no es válido en el cliente. */
  tokenExpirado(token) {
    const t = token || localStorage.getItem('token');
    if (!t) return true;
    try {
      const part = t.split('.')[1];
      if (!part) return true;
      const b64 = part.replace(/-/g, '+').replace(/_/g, '/');
      const pad = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
      const payload = JSON.parse(atob(pad));
      if (!payload.exp) return false;
      return Date.now() >= (payload.exp * 1000) - 3000;
    } catch {
      return true;
    }
  },

  /**
   * Cierra sesión en el cliente y manda al login.
   * Evita bucles si varios fetch 401 llegan a la vez.
   */
  forzarCierreSesion(motivo) {
    if (this._cerrandoSesion) return;
    this._cerrandoSesion = true;
    if (motivo) sessionStorage.setItem('sesion_msg', motivo);
    sessionStorage.setItem('logout', '1');
    localStorage.clear();
    window.location.href = '/';
  },

  irLogin() {
    this.forzarCierreSesion();
  },

  /** Intercepta 401 de cualquier fetch hacia la API. */
  instalarInterceptorAuth() {
    if (this._fetchPatched || typeof window === 'undefined') return;
    this._fetchPatched = true;
    const orig = window.fetch.bind(window);
    const self = this;
    window.fetch = async function diabcareFetch(...args) {
      const res = await orig(...args);
      if (res.status !== 401) return res;
      let url = '';
      try {
        const req = args[0];
        url = typeof req === 'string' ? req : (req && req.url) || '';
      } catch (_) { /* ignore */ }
      if (/\/api\/auth\/(login|logout|recuperar|resetear|solicitud|registro)/i.test(url)) {
        return res;
      }
      if (localStorage.getItem('token')) {
        self.forzarCierreSesion('Tu sesión expiró. Inicia sesión de nuevo.');
      }
      return res;
    };
  },

  /** Comprueba exp del JWT al cargar y cada rato / al volver a la pestaña. */
  iniciarVigilanciaSesion() {
    if (this._vigilanciaOn) return;
    this._vigilanciaOn = true;
    const tick = () => {
      const t = localStorage.getItem('token');
      if (!t) return;
      if (this.tokenExpirado(t)) {
        this.forzarCierreSesion('Tu sesión expiró. Inicia sesión de nuevo.');
      }
    };
    tick();
    setInterval(tick, 12000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') tick();
    });
  },

  irPerfil() {
    window.location.href = '/paginas/seguridad/perfil/index.html';
  },

  homeParaRol(rol) {
    return this.HOME_POR_ROL[rol] || '/paginas/clinico/analisis/index.html';
  },

  guardRol(roles) {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (!u.rol) { this.irLogin(); return; }
    if (!roles.includes(u.rol)) {
      window.location.href = this.homeParaRol(u.rol);
    }
  },
};

window.toggle = (h) => DiabCareNav.toggle(h);
window.cerrarSesion = () => DiabCareNav.cerrarSesion();

(function bootSesionDiabCare() {
  try {
    const path = (window.location && window.location.pathname) || '';
    const enLogin = path === '/' || path === '/index.html'
      || path.includes('/seguridad/autenticacion');
    if (enLogin) return;
    DiabCareNav.instalarInterceptorAuth();
    DiabCareNav.iniciarVigilanciaSesion();
  } catch (_) { /* ignore */ }
})();
