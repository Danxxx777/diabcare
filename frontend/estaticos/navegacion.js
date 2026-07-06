/**
 * DiabCare Analytics — navegación alineada a paquetes P1–P15 (GA07).
 * Demo activo: P1–P8, P11, P12, P14 + vistas P5/P6/P7.
 * P9, P10, P13, P15 marcados como "próximo" (iteración posterior).
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

  MODULOS_NAVEGABLES: [
    'pacientes', 'admisiones', 'citas', 'mis_citas', 'registros', 'analisis', 'prediccion', 'reportes',
    'dataset', 'pipeline', 'modelo',
    'usuarios', 'auditoria', 'configuracion', 'notificaciones',
  ],

  MODULOS_PROXIMO: [],

  CATEGORIAS: [
    {
      id: 'clinico',
      label: 'Operaciones clínicas',
      items: [
        { modulo: 'pacientes', label: 'Pacientes / HCE', subs: [
          { href: '/paginas/clinico/pacientes/index.html', label: 'Expedientes' },
        ]},
        { modulo: 'admisiones', label: 'Admisiones', subs: [
          { href: '/paginas/clinico/admisiones/index.html', label: 'Ingresos hospitalarios' },
        ]},
        { modulo: 'citas', label: 'Agenda', subs: [
          { href: '/paginas/clinico/agenda/index.html', label: 'Citas médicas' },
        ]},
        { modulo: 'mis_citas', label: 'Mis citas', subs: [
          { href: '/paginas/clinico/mis_citas/index.html', label: 'Agenda asignada' },
        ]},
        { modulo: 'registros', label: 'Consultas', subs: [
          { href: '/paginas/clinico/registros_clinicos/index.html', label: 'CRUD y filtros' },
        ]},
        { modulo: 'analisis', label: 'Análisis / BI', subs: [
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
          { href: '/paginas/datos/modelo_ml/index.html', label: 'Entrenamiento e historial' },
        ]},
      ],
    },
    {
      id: 'gobierno',
      label: 'Seguridad y cumplimiento',
      items: [
        { modulo: 'usuarios', label: 'Usuarios', subs: [
          { href: '/paginas/seguridad/usuarios/index.html', label: 'Cuentas y roles' },
        ]},
        { modulo: 'auditoria', label: 'Auditoría', subs: [
          { href: '/paginas/gobierno/auditoria/index.html', label: 'Registro de eventos' },
        ]},
        { modulo: 'configuracion', label: 'Configuración', subs: [
          { href: '/paginas/gobierno/configuracion/index.html', label: 'Parámetros del sistema' },
        ]},
        { modulo: 'notificaciones', label: 'Notificaciones', subs: [
          { href: '/paginas/notificaciones/index.html', label: 'Alertas y correo' },
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

  ACCESO: {
    administrador: [
      'pacientes', 'admisiones', 'citas', 'registros', 'analisis', 'prediccion', 'reportes',
      'dataset', 'pipeline', 'modelo',
      'usuarios', 'auditoria', 'configuracion', 'notificaciones',
    ],
    medico: [
      'pacientes', 'mis_citas', 'registros', 'analisis', 'prediccion', 'reportes',
      'notificaciones',
    ],
    analista: [
      'analisis', 'prediccion', 'dataset', 'pipeline', 'modelo', 'reportes', 'notificaciones',
    ],
  },

  _moduloDesdeRuta(href) {
    const mapa = [
      ['/paginas/clinico/pacientes/', 'pacientes'],
      ['/paginas/clinico/admisiones/', 'admisiones'],
      ['/paginas/clinico/agenda/', 'citas'],
      ['/paginas/clinico/mis_citas/', 'mis_citas'],
      ['/paginas/clinico/registros_clinicos/', 'registros'],
      ['/paginas/clinico/analisis/', 'analisis'],
      ['/paginas/clinico/analisis/estadisticas/', 'analisis'],
      ['/paginas/clinico/prediccion/', 'prediccion'],
      ['/paginas/clinico/reportes/', 'reportes'],
      ['/paginas/datos/dataset/', 'dataset'],
      ['/paginas/datos/pipeline_elt/', 'pipeline'],
      ['/paginas/datos/modelo_ml/', 'modelo'],
      ['/paginas/seguridad/usuarios/', 'usuarios'],
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
        <div><div class="logo-text">DiabCare</div><div class="logo-sub">Analytics</div></div>
      </div>
      <nav class="nav">${navHtml}</nav>
      <div class="sidebar-bottom">
        <div class="user-row-wrap">
          <button type="button" class="user-row user-row-btn" onclick="DiabCareNav.irPerfil()" title="Mi perfil">
            <div class="user-avatar" id="userAvatar">A</div>
            <div class="user-info">
              <div class="user-name" id="userName">Cargando...</div>
              <div class="user-rol" id="userRol">—</div>
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
    if (!localStorage.getItem('token')) {
      this.irLogin();
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

  cerrarSesion() {
    sessionStorage.setItem('logout', '1');
    localStorage.clear();
    window.location.href = '/';
  },

  irLogin() {
    localStorage.clear();
    window.location.href = '/';
  },

  irPerfil() {
    window.location.href = '/paginas/seguridad/perfil/index.html';
  },

  guardRol(roles) {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (u.rol && !roles.includes(u.rol)) {
      window.location.href = '/paginas/clinico/analisis/index.html';
    }
  },
};

window.toggle = (h) => DiabCareNav.toggle(h);
window.cerrarSesion = () => DiabCareNav.cerrarSesion();
