/**
 * DiabCare — barra lateral compartida (P1–P15).
 * Alcance demo GA07: flujo de datos (origen → ELT → consulta → ML → reporte → auditoría).
 * Fuera de demo: corporativo, notificaciones, benchmarking, integraciones.
 */
window.DiabCareNav = {
  /** Backend FastAPI — siempre puerto 8000 aunque la página se abra con Live Server u otro puerto */
  getApi() {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    const { protocol, hostname, port, origin } = window.location;
    if (port === '8000') return origin;
    const host = hostname && hostname !== '' ? hostname : 'localhost';
    return `${protocol}//${host}:8000`;
  },
  get API() { return this.getApi(); },

  /** Módulos presentables en la entrega GA07 (10 paquetes) */
  PRESENTACION: [
    'analisis', 'registros', 'dataset', 'usuarios', 'prediccion',
    'pipeline', 'modelo', 'reportes', 'auditoria', 'configuracion',
  ],

  ACCESO: {
    administrador: [
      'analisis', 'registros', 'dataset', 'usuarios', 'prediccion',
      'pipeline', 'modelo', 'reportes', 'auditoria', 'configuracion',
    ],
    medico: ['analisis', 'registros', 'prediccion', 'reportes'],
    analista: ['analisis', 'dataset', 'prediccion', 'pipeline', 'modelo'],
  },

  GRUPOS: [
    { section: 'Principal', items: [
      { modulo: 'analisis', label: 'Análisis', subs: [
        { href: '/paginas/analisis/index.html', label: 'Dashboard' },
        { href: '/paginas/estadisticas/index.html', label: 'Estadísticas' },
      ]},
      { modulo: 'registros', label: 'Registros clínicos', subs: [
        { href: '/paginas/registros_clinicos/index.html', label: 'Consultar / Filtrar' },
      ]},
      { modulo: 'dataset', label: 'Dataset', subs: [
        { href: '/paginas/dataset/index.html', label: 'Ver tablas' },
        { href: '/paginas/dataset/generador.html', label: 'Generador de datos' },
      ]},
      { modulo: 'usuarios', label: 'Usuarios', subs: [
        { href: '/paginas/usuarios/index.html', label: 'Gestionar usuarios' },
      ]},
    ]},
    { section: 'Datos', items: [
      { modulo: 'prediccion', label: 'Predicción ML', subs: [
        { href: '/paginas/prediccion/index.html', label: 'Predecir / Métricas' },
      ]},
      { modulo: 'pipeline', label: 'Pipeline ELT', subs: [
        { href: '/paginas/pipeline_etl/index.html', label: 'Estado / Archivos' },
      ]},
      { modulo: 'modelo', label: 'Modelo ML', subs: [
        { href: '/paginas/modelo_ml/index.html', label: 'Gestión del modelo' },
      ]},
    ]},
    { section: 'Sistema', items: [
      { modulo: 'reportes', label: 'Reportes', subs: [
        { href: '/paginas/reportes/index.html', label: 'Generar / Descargar' },
      ]},
      { modulo: 'auditoria', label: 'Auditoría', subs: [
        { href: '/paginas/auditoria/index.html', label: 'Registro de eventos' },
      ]},
      { modulo: 'configuracion', label: 'Configuración', subs: [
        { href: '/paginas/configuracion/index.html', label: 'Ajustes del sistema' },
      ]},
      { modulo: 'corporativo', label: 'Corporativo', subs: [
        { href: '/paginas/corporativo/index.html', label: 'Información institucional' },
      ]},
      { modulo: 'notificaciones', label: 'Notificaciones', subs: [
        { href: '/paginas/notificaciones/index.html', label: 'Centro de alertas' },
      ]},
      { modulo: 'benchmarking', label: 'Benchmarking', subs: [
        { href: '/paginas/benchmarking/index.html', label: 'Comparativa de KPIs' },
      ]},
      { modulo: 'integraciones', label: 'Integraciones', subs: [
        { href: '/paginas/integraciones/index.html', label: 'API e integraciones' },
      ]},
    ]},
  ],

  _moduloDesdeRuta(href) {
    const mapa = {
      '/paginas/analisis/': 'analisis',
      '/paginas/estadisticas/': 'analisis',
      '/paginas/registros_clinicos/': 'registros',
      '/paginas/dataset/': 'dataset',
      '/paginas/usuarios/': 'usuarios',
      '/paginas/prediccion/': 'prediccion',
      '/paginas/pipeline_etl/': 'pipeline',
      '/paginas/modelo_ml/': 'modelo',
      '/paginas/reportes/': 'reportes',
      '/paginas/auditoria/': 'auditoria',
      '/paginas/configuracion/': 'configuracion',
      '/paginas/corporativo/': 'corporativo',
      '/paginas/notificaciones/': 'notificaciones',
      '/paginas/benchmarking/': 'benchmarking',
      '/paginas/integraciones/': 'integraciones',
    };
    for (const [prefijo, modulo] of Object.entries(mapa)) {
      if (href.includes(prefijo)) return modulo;
    }
    return null;
  },

  init(activeHref) {
    const href = activeHref || window.location.pathname;
    const modulo = this._moduloDesdeRuta(href);
    if (modulo && !this.PRESENTACION.includes(modulo)) {
      window.location.href = '/paginas/analisis/index.html';
      return;
    }
    this.render(href);
    this.initUser();
    this.aplicarRoles();
  },

  render(activeHref) {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;

    let navHtml = '';
    for (const block of this.GRUPOS) {
      navHtml += `<div class="nav-section">${block.section}</div>`;
      for (const item of block.items) {
        if (!this.PRESENTACION.includes(item.modulo)) {
          navHtml += `<div class="nav-group" data-modulo="${item.modulo}">`;
          navHtml += `<div class="nav-group-header disabled">`;
          navHtml += `<span class="nav-group-icon">&#9681;</span><span class="nav-group-label">${item.label}</span>`;
          navHtml += `<span class="nav-badge">pronto</span></div></div>`;
          continue;
        }
        const isActiveGroup = item.subs.some(s =>
          activeHref.startsWith(s.href.replace(/\.html$/, '')));
        navHtml += `<div class="nav-group" data-modulo="${item.modulo}">`;
        navHtml += `<div class="nav-group-header${isActiveGroup ? ' open' : ''}" onclick="DiabCareNav.toggle(this)">`;
        navHtml += `<span class="nav-group-icon">&#9681;</span><span class="nav-group-label">${item.label}</span>`;
        navHtml += `<i class="nav-chevron">&#8250;</i></div>`;
        navHtml += `<div class="nav-sub${isActiveGroup ? ' open' : ''}">`;
        for (const sub of item.subs) {
          const active = activeHref === sub.href || activeHref.endsWith(sub.href);
          navHtml += `<a class="nav-sub-item${active ? ' active' : ''}" href="${sub.href}">`;
          navHtml += `<div class="nav-dot"></div><span class="nav-sub-label">${sub.label}</span></a>`;
        }
        navHtml += `</div></div>`;
      }
    }

    mount.innerHTML = `
      <div class="logo-area">
        <div class="logo-mark">D</div>
        <div><div class="logo-text">DiabCare</div></div>
      </div>
      <nav class="nav">${navHtml}</nav>
      <div class="sidebar-bottom">
        <div class="user-row-wrap" style="display:flex;flex-direction:row;align-items:center;gap:6px;">
          <div class="user-row">
            <div class="user-avatar" id="userAvatar">A</div>
            <div><div class="user-name" id="userName">Cargando...</div><div class="user-rol" id="userRol">—</div></div>
          </div>
          <button class="btn-logout" onclick="DiabCareNav.cerrarSesion()" title="Cerrar sesión">⏻</button>
        </div>
        <div class="ver-info">DiabCare Analytics v2.0 · GA07</div>
      </div>`;
  },

  toggle(h) {
    h.classList.toggle('open');
    const s = h.nextElementSibling;
    if (s) s.classList.toggle('open');
  },

  initUser() {
    if (!localStorage.getItem('token')) {
      window.location.href = '/';
      return;
    }
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const nameEl = document.getElementById('userName');
    if (nameEl && u.nombre) {
      nameEl.textContent = u.nombre;
      document.getElementById('userRol').textContent = u.rol || '';
      document.getElementById('userAvatar').textContent = u.nombre[0].toUpperCase();
    }
  },

  aplicarRoles() {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const rol = u.rol || '';
    const permitidos = this.ACCESO[rol];
    if (!permitidos) return;
    document.querySelectorAll('.nav-group[data-modulo]').forEach(g => {
      if (!permitidos.includes(g.dataset.modulo)) g.style.display = 'none';
    });
  },

  cerrarSesion() {
    localStorage.clear();
    window.location.href = '/';
  },

  guardRol(roles) {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (u.rol && !roles.includes(u.rol)) {
      window.location.href = '/paginas/analisis/index.html';
    }
  },
};

window.toggle = (h) => DiabCareNav.toggle(h);
window.cerrarSesion = () => DiabCareNav.cerrarSesion();
