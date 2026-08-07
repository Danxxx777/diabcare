/**
 * DiabCare Hospital - navegación por departamentos y roles.
 * Matriz de acceso por rol (admin = supervisión total).
 */
(function _temaAlCargar() {
  try {
    const t = localStorage.getItem('diabcare_tema') || 'oscuro';
    document.documentElement.setAttribute('data-tema', t === 'claro' ? 'claro' : 'oscuro');
    const idi = localStorage.getItem('diabcare_idioma') || 'es';
    document.documentElement.setAttribute('lang', idi === 'en' ? 'en' : 'es');
  } catch (_) { /* ignore */ }
})();

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
    administrador: '/paginas/clinico/analisis/informes/index.html',
    medico: '/paginas/clinico/analisis/informes/index.html',
    enfermero: '/paginas/clinico/analisis/informes/index.html',
    farmaceutico: '/paginas/clinico/analisis/informes/index.html',
    analista: '/paginas/clinico/analisis/informes/index.html',
  },

  MODULOS_NAVEGABLES: [
    'pacientes', 'admisiones', 'urgencias', 'citas', 'mis_citas', 'registros',
    'laboratorio', 'comorbilidades',
    'recetas', 'farmacia', 'facturacion', 'rrhh',
    'analisis', 'prediccion', 'reportes',
    'dataset', 'pipeline', 'modelo',
    'usuarios', 'auditoria', 'configuracion', 'notificaciones',
  ],

  MODULOS_PROXIMO: [],

  /**
   * Menú por FUNCIÓN (alineado a MODULOS_POR_CATEGORIA del backend).
   * - Clínico = operación del día (no estadísticas).
   * - Análisis = panel, informes, predicción, PDF (aunque vivan bajo /clinico/).
   * - Negocio / Farmacia / Datos / Gobierno / Seguridad = su área.
   * Ítems en orden alfabético (etiqueta ES). Visibilidad real = ACCESO[rol].
   */
  CATEGORIAS: [
    {
      id: 'clinico',
      labelKey: 'cat_clinico',
      items: [
        { modulo: 'admisiones', labelKey: 'admisiones', subs: [
          { href: '/paginas/clinico/admisiones/index.html', labelKey: 'sub_ingresos' },
        ]},
        { modulo: 'comorbilidades', labelKey: 'comorbilidades', subs: [
          { href: '/paginas/clinico/comorbilidades/index.html', labelKey: 'sub_complicaciones' },
        ]},
        { modulo: 'registros', labelKey: 'registros', subs: [
          { href: '/paginas/clinico/registros_clinicos/index.html', labelKey: 'sub_registro' },
        ]},
        { modulo: 'laboratorio', labelKey: 'laboratorio', subs: [
          { href: '/paginas/clinico/laboratorio/index.html', labelKey: 'sub_ordenes' },
        ]},
        { modulo: 'mis_citas', labelKey: 'mis_citas', subs: [
          { href: '/paginas/clinico/mis_citas/index.html', labelKey: 'sub_turnos' },
        ]},
        { modulo: 'pacientes', labelKey: 'pacientes', subs: [
          { href: '/paginas/clinico/pacientes/index.html', labelKey: 'sub_expedientes' },
        ]},
        { modulo: 'citas', labelKey: 'citas', subs: [
          { href: '/paginas/clinico/agenda/index.html', labelKey: 'sub_agenda' },
        ]},
        { modulo: 'urgencias', labelKey: 'urgencias', subs: [
          { href: '/paginas/clinico/urgencias/index.html', labelKey: 'sub_triage' },
        ]},
      ],
    },
    {
      id: 'analisis',
      labelKey: 'cat_analisis',
      items: [
        { modulo: 'analisis', icon: 'analisis', labelKey: 'calidad_dm', subs: [
          { href: '/paginas/clinico/analisis/diabetes/index.html', labelKey: 'sub_calidad', roles: ['administrador', 'medico', 'analista'] },
        ]},
        { modulo: 'analisis', icon: 'panel', labelKey: 'panel', subs: [
          { href: '/paginas/clinico/analisis/informes/index.html', labelKey: 'sub_panel' },
        ]},
        { modulo: 'prediccion', labelKey: 'prediccion', subs: [
          { href: '/paginas/clinico/prediccion/index.html', labelKey: 'sub_inferencia' },
        ]},
        { modulo: 'reportes', icon: 'pdf', labelKey: 'reportes', subs: [
          { href: '/paginas/clinico/reportes/index.html', labelKey: 'sub_pdf' },
        ]},
      ],
    },
    {
      id: 'datos',
      labelKey: 'cat_datos',
      items: [
        { modulo: 'dataset', labelKey: 'dataset', subs: [
          { href: '/paginas/datos/dataset/generador.html', labelKey: 'sub_generador' },
          { href: '/paginas/datos/dataset/index.html', labelKey: 'sub_hechos' },
        ]},
        { modulo: 'modelo', labelKey: 'modelo', subs: [
          { href: '/paginas/datos/modelo_ml/index.html', labelKey: 'sub_entrenamiento' },
        ]},
        { modulo: 'pipeline', labelKey: 'pipeline', subs: [
          { href: '/paginas/datos/pipeline_elt/index.html', labelKey: 'sub_estado' },
        ]},
      ],
    },
    {
      id: 'farmacia_rx',
      labelKey: 'cat_farmacia_rx',
      items: [
        { modulo: 'farmacia', labelKey: 'farmacia', subs: [
          { href: '/paginas/negocio/farmacia/index.html', labelKey: 'sub_inventario' },
        ]},
        { modulo: 'recetas', labelKey: 'recetas', subs: [
          { href: '/paginas/negocio/recetas/index.html', labelKey: 'sub_prescripciones' },
        ]},
      ],
    },
    {
      id: 'gobierno',
      labelKey: 'cat_gobierno',
      items: [
        { modulo: 'auditoria', labelKey: 'auditoria', subs: [
          { href: '/paginas/gobierno/auditoria/index.html', labelKey: 'sub_eventos' },
        ]},
        { modulo: 'configuracion', labelKey: 'configuracion', subs: [
          { href: '/paginas/gobierno/configuracion/index.html', labelKey: 'sub_ajustes' },
        ]},
      ],
    },
    {
      id: 'negocio',
      labelKey: 'cat_negocio',
      items: [
        { modulo: 'facturacion', labelKey: 'facturacion', subs: [
          { href: '/paginas/negocio/facturacion/index.html', labelKey: 'sub_facturacion' },
        ]},
        { modulo: 'rrhh', labelKey: 'rrhh', subs: [
          { href: '/paginas/negocio/rrhh/index.html', labelKey: 'sub_costeo' },
        ]},
      ],
    },
    {
      id: 'seguridad',
      labelKey: 'cat_seguridad',
      items: [
        { modulo: 'notificaciones', labelKey: 'notificaciones', subs: [
          { href: '/paginas/seguridad/notificaciones/index.html', labelKey: 'sub_bandeja' },
        ]},
        { modulo: 'usuarios', labelKey: 'usuarios', subs: [
          { href: '/paginas/seguridad/usuarios/index.html', labelKey: 'sub_cuentas' },
        ]},
      ],
    },
  ],

  t(key) {
    if (window.DiabCareI18n && typeof DiabCareI18n.t === 'function') return DiabCareI18n.t(key);
    return key;
  },

  _txt(obj) {
    if (!obj) return '';
    if (obj.labelKey) return this.t(obj.labelKey);
    return obj.label || '';
  },

  get PRESENTACION() {
    return this.MODULOS_NAVEGABLES.slice();
  },

  _esProximo(item) {
    return item.pronto === true || this.MODULOS_PROXIMO.includes(item.modulo);
  },

  /**
   * Quién ve qué (espejo de PERMISOS_MODULOS en Dependencias.py).
   * Categoría vacía para el rol → no se muestra en el sidebar.
   *
   *   médico      → Clínico (consulta) + Análisis + Recetas + Notif
   *   enfermero   → Clínico (recepción/lab/urgencias) + Notif  (sin Análisis)
   *   farmacéutico→ Clínico (recepción) + Farmacia + Negocio(caja) + Análisis básico
   *   analista    → Análisis + Datos + Negocio(lectura) + Notif  (sin Clínico operativo)
   *   admin       → todo (supervisión)
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

  /** Módulos permitidos al rol actual (o null = sin filtro). */
  _permitidosRol() {
    try {
      const rol = String((JSON.parse(localStorage.getItem('usuario') || '{}').rol || '')).toLowerCase();
      return this.ACCESO[rol] || null;
    } catch {
      return null;
    }
  },

  _itemVisibleParaRol(item, permitidos) {
    if (!permitidos) return true;
    if (!permitidos.includes(item.modulo)) return false;
    const subs = this._subsVisibles(item.subs);
    return subs.length > 0;
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
      ['/paginas/seguridad/notificaciones/', 'notificaciones'],
      ['/paginas/gobierno/auditoria/', 'auditoria'],
      ['/paginas/gobierno/configuracion/', 'configuracion'],
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

  /** Filtra subenlaces con restricción opcional `roles: [...]` según el rol actual */
  _subsVisibles(subs) {
    const rol = String((JSON.parse(localStorage.getItem('usuario') || '{}').rol || '')).toLowerCase();
    return (subs || []).filter(s => !s.roles || s.roles.includes(rol));
  },

  _itemHtml(item, activeHref) {
    const proximo = this._esProximo(item);
    const subs = this._subsVisibles(item.subs);
    if (!subs.length) return '';

    const label = this._txt(item);
    const title = String(label).replace(/"/g, '&quot;');

    if (subs.length === 1) {
      const sub = subs[0];
      const active = activeHref === sub.href || activeHref.endsWith(sub.href);
      const badge = proximo ? '<span class="nav-badge">próximo</span>' : '';
      return `<a class="nav-group-link${active ? ' active' : ''}${proximo ? ' nav-link-proximo' : ''}" href="${sub.href}" data-modulo="${item.modulo}" title="${title}"${proximo ? ' data-proximo="1"' : ''}>
        <span class="nav-group-icon">${DiabCareIcons.nav(item.icon || item.modulo)}</span>
        <span class="nav-group-label">${label}</span>${badge}
      </a>`;
    }

    const isActiveGroup = subs.some(s =>
      activeHref.startsWith(s.href.replace(/\.html$/, '')));
    const primary = subs[0].href;
    let html = `<div class="nav-group${proximo ? ' nav-group-proximo' : ''}" data-modulo="${item.modulo}"${proximo ? ' data-proximo="1"' : ''}>`;
    html += `<div class="nav-group-header${isActiveGroup ? ' open' : ''}" onclick="DiabCareNav.toggleModulo(this)" title="${title}" data-primary-href="${primary}">`;
    html += `<span class="nav-group-icon">${DiabCareIcons.nav(item.icon || item.modulo)}</span>`;
    html += `<span class="nav-group-label">${label}</span>`;
    if (proximo) html += '<span class="nav-badge">próximo</span>';
    html += `<span class="nav-chevron">${DiabCareIcons.svg('chevron', 12)}</span></div>`;
    html += `<div class="nav-sub${isActiveGroup ? ' open' : ''}">`;
    for (const sub of subs) {
      const active = activeHref === sub.href || activeHref.endsWith(sub.href);
      html += `<a class="nav-sub-item${active ? ' active' : ''}" href="${sub.href}">`;
      html += `<div class="nav-dot"></div><span class="nav-sub-label">${this._txt(sub)}</span></a>`;
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
    this.aplicarEstadoColapsado();
    this.montarTopbarAcciones();
    if (window.DiabCareI18n) DiabCareI18n.aplicarPagina();
    if (typeof DiabCareAPI !== 'undefined') {
      DiabCareAPI.actualizarEstadoTopbar();
    }
  },

  render(activeHref) {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    const href = activeHref || window.location.pathname;
    const permitidos = this._permitidosRol();

    let navHtml = '';
    const catActiva = this._categoriaActiva(href);
    for (const cat of this.CATEGORIAS) {
      const items = cat.items.filter(it => this._itemVisibleParaRol(it, permitidos));
      if (!items.length) continue; // categoría vacía para este rol → no pintar
      const abierta = cat.id === catActiva;
      navHtml += `<div class="nav-cat-block" data-categoria="${cat.id}">`;
      navHtml += `<button type="button" class="nav-cat-header${abierta ? ' open' : ''}" onclick="DiabCareNav.toggleCategoria(this)" aria-expanded="${abierta}">`;
      navHtml += `<span class="nav-cat-label">${this._txt(cat)}</span>`;
      navHtml += `<span class="nav-chevron">${DiabCareIcons.svg('chevron', 12)}</span>`;
      navHtml += `</button>`;
      navHtml += `<div class="nav-categoria${abierta ? ' open' : ''}">`;
      for (const item of items) {
        navHtml += this._itemHtml(item, href);
      }
      navHtml += '</div></div>';
    }

    const titColapso = this.t('tb_colapsar');
    const hospital = this.t('hospital');

    mount.innerHTML = `
      <div class="logo-area">
        <img class="logo-mark" src="/estaticos/img/logo-icon.svg" alt="DiabCare" width="28" height="28">
        <div class="logo-copy"><div class="logo-text">DiabCare</div><div class="logo-sub">${hospital}</div></div>
        <button type="button" class="sidebar-toggle" onclick="DiabCareNav.toggleColapso()" title="${titColapso}" aria-label="${titColapso}">
          ${DiabCareIcons.svg('chevron', 14)}
        </button>
      </div>
      <nav class="nav">${navHtml}</nav>`;
  },

  estaColapsada() {
    return localStorage.getItem('diabcare_sidebar_colapsada') === '1';
  },

  aplicarEstadoColapsado() {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    const colapsada = this.estaColapsada();
    // Solo toggle de clase: el CSS (.sidebar.collapsed .nav-categoria) ya muestra los ítems.
    // Evita abrir/cerrar cientos de nodos en JS (eso hacía el colapso lento).
    mount.classList.toggle('collapsed', colapsada);
    document.body.classList.toggle('sidebar-collapsed', colapsada);
  },

  toggleColapso() {
    const next = this.estaColapsada() ? '0' : '1';
    localStorage.setItem('diabcare_sidebar_colapsada', next);
    this.aplicarEstadoColapsado();
  },

  temaActual() {
    return document.documentElement.getAttribute('data-tema') === 'claro' ? 'claro' : 'oscuro';
  },

  aplicarTema(tema) {
    const t = tema === 'claro' ? 'claro' : 'oscuro';
    document.documentElement.setAttribute('data-tema', t);
    localStorage.setItem('diabcare_tema', t);
    const btn = document.getElementById('tb-tema');
    if (btn) {
      const oscuro = t === 'oscuro';
      btn.title = this.t(oscuro ? 'tb_tema_claro' : 'tb_tema_oscuro');
      btn.setAttribute('aria-label', btn.title);
      btn.innerHTML = DiabCareIcons.svg(oscuro ? 'sol' : 'luna', 16);
    }
  },

  toggleTema() {
    this.aplicarTema(this.temaActual() === 'oscuro' ? 'claro' : 'oscuro');
  },

  idiomaActual() {
    if (window.DiabCareI18n) return DiabCareI18n.idioma();
    return localStorage.getItem('diabcare_idioma') === 'en' ? 'en' : 'es';
  },

  setIdioma(cod) {
    const idi = cod === 'en' ? 'en' : 'es';
    localStorage.setItem('diabcare_idioma', idi);
    document.documentElement.setAttribute('lang', idi);
    try {
      const u = JSON.parse(localStorage.getItem('usuario') || '{}');
      u.idioma = idi;
      localStorage.setItem('usuario', JSON.stringify(u));
    } catch (_) { /* ignore */ }
    const menu = document.getElementById('tb-idioma-menu');
    if (menu) menu.hidden = true;

    // Re-pintar menú, topbar y títulos de página
    const href = window.location.pathname;
    this.render(href);
    this.initUser();
    this.aplicarRoles();
    this.aplicarEstadoColapsado();
    const prev = document.getElementById('tb-acciones');
    if (prev) prev.remove();
    this.montarTopbarAcciones(true);
    if (window.DiabCareI18n) DiabCareI18n.aplicarPagina();

    if (typeof DiabCareAPI !== 'undefined' && DiabCareAPI.toast) {
      DiabCareAPI.toast(this.t('idioma_ok'), 'success');
    }
  },

  /** Acciones fijas a la derecha del topbar (tema, idioma, notificaciones, config, perfil). */
  montarTopbarAcciones(forzar) {
    const topbar = document.querySelector('.main .topbar');
    if (!topbar) return;
    if (!forzar && topbar.querySelector('#tb-acciones')) return;

    let right = topbar.querySelector('.tb-right');
    if (!right) {
      right = document.createElement('div');
      right.className = 'tb-right';
      topbar.appendChild(right);
    }

    // Quitar chip MinIO / acciones previas: el perfil ocupa ese lugar
    right.querySelectorAll('.tb-online, #tb-acciones, .tb-user-wrap').forEach(el => el.remove());

    const acciones = document.createElement('div');
    acciones.id = 'tb-acciones';
    acciones.className = 'tb-acciones';

    const tema = this.temaActual();
    const idi = this.idiomaActual();
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const rol = (u.rol || '').toLowerCase();
    const permitidos = this.ACCESO[rol] || [];
    const verNotif = !permitidos.length || permitidos.includes('notificaciones');
    const verConfig = permitidos.includes('configuracion');
    const hrefConfig = verConfig
      ? '/paginas/gobierno/configuracion/index.html'
      : '/paginas/seguridad/perfil/index.html';
    const titleConfig = this.t(verConfig ? 'tb_config' : 'tb_preferencias');
    const titleTema = this.t(tema === 'oscuro' ? 'tb_tema_claro' : 'tb_tema_oscuro');
    const letra = ((u.nombre || 'U')[0] || 'U').toUpperCase();

    acciones.innerHTML = `
      <button type="button" class="tb-icon-btn" id="tb-tema" title="${titleTema}" onclick="DiabCareNav.toggleTema()">
        ${DiabCareIcons.svg(tema === 'oscuro' ? 'sol' : 'luna', 16)}
      </button>
      <div class="tb-menu-wrap">
        <button type="button" class="tb-icon-btn" id="tb-idioma" title="${this.t('tb_idioma')}" onclick="DiabCareNav.toggleMenuIdioma(event)">
          ${DiabCareIcons.svg('idioma', 16)}
          <span class="tb-idioma-lab" id="tb-idioma-lab">${idi.toUpperCase()}</span>
        </button>
        <div class="tb-dropdown" id="tb-idioma-menu" hidden>
          <button type="button" data-idi="es" onclick="DiabCareNav.setIdioma('es')">Español</button>
          <button type="button" data-idi="en" onclick="DiabCareNav.setIdioma('en')">English</button>
        </div>
      </div>
      ${verNotif ? `
      <div class="tb-menu-wrap">
        <button type="button" class="tb-icon-btn" id="tb-notif" title="${this.t('tb_notif')}" onclick="DiabCareNav.togglePanelNotif(event)" aria-expanded="false">
          ${DiabCareIcons.svg('notificaciones', 16)}
          <span class="tb-badge" id="tb-notif-badge" hidden>0</span>
        </button>
        <div class="tb-notif-panel" id="tb-notif-panel" hidden>
          <div class="tb-notif-head">
            <strong>${this.t('tb_notif')}</strong>
            <div class="tb-notif-actions">
              <button type="button" onclick="DiabCareNav.marcarTodasNotif(event)">${this.t('tb_notif_marcar')}</button>
            </div>
          </div>
          <div class="tb-notif-lista" id="tb-notif-lista">
            <div class="tb-notif-loading">${this.t('cargando')}</div>
          </div>
          <div class="tb-notif-foot">
            <a href="/paginas/seguridad/notificaciones/index.html">${this.t('tb_notif_ver')}</a>
          </div>
        </div>
      </div>` : ''}
      <a class="tb-icon-btn" id="tb-config" href="${hrefConfig}" title="${titleConfig}">
        ${DiabCareIcons.svg('configuracion', 16)}
      </a>
    `;
    right.appendChild(acciones);

    const userWrap = document.createElement('div');
    userWrap.className = 'tb-user-wrap';
    userWrap.innerHTML = `
      <button type="button" class="tb-user" id="tb-user" title="${this.t('tb_perfil')}" onclick="DiabCareNav.toggleMenuUsuario(event)" aria-expanded="false">
        <span class="tb-user-avatar" id="tb-user-avatar">${letra}</span>
        <span class="tb-user-meta">
          <span class="tb-user-name" id="tb-user-name">${u.nombre || this.t('cargando')}</span>
          <span class="tb-user-rol" id="tb-user-rol">${this.etiquetaRol(u.rol)}</span>
        </span>
      </button>
      <div class="tb-dropdown tb-user-menu" id="tb-user-menu" hidden>
        <div class="tb-menu-status" id="tb-storage-status">
          <span class="dot" id="tb-storage-dot"></span>
          <span id="tb-storage-label">…</span>
        </div>
        <a class="tb-menu-link" href="/paginas/seguridad/perfil/index.html">${this.t('tb_perfil')}</a>
        <button type="button" class="tb-menu-danger" onclick="DiabCareNav.cerrarSesion()">${this.t('tb_logout')}</button>
      </div>
    `;
    right.appendChild(userWrap);

    this.pintarAvatarTopbar(u);

    if (!this._topbarClickBound) {
      this._topbarClickBound = true;
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.tb-menu-wrap') && !e.target.closest('.tb-user-wrap')) {
          this.cerrarMenusTopbar();
        }
      });
    }

    if (verNotif) this.cargarBadgeNotificaciones();
    if (typeof DiabCareAPI !== 'undefined') DiabCareAPI.actualizarEstadoTopbar();
  },

  cerrarMenusTopbar(excepto) {
    const pares = [
      ['tb-idioma-menu', 'tb-idioma'],
      ['tb-notif-panel', 'tb-notif'],
      ['tb-user-menu', 'tb-user'],
    ];
    for (const [id, btnId] of pares) {
      if (excepto === id) continue;
      const el = document.getElementById(id);
      if (el) el.hidden = true;
      const btn = document.getElementById(btnId);
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  },

  toggleMenuIdioma(ev) {
    if (ev) ev.stopPropagation();
    const menu = document.getElementById('tb-idioma-menu');
    if (!menu) return;
    const open = menu.hidden;
    this.cerrarMenusTopbar(open ? 'tb-idioma-menu' : null);
    menu.hidden = !open;
    const btn = document.getElementById('tb-idioma');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  },

  toggleMenuUsuario(ev) {
    if (ev) ev.stopPropagation();
    const menu = document.getElementById('tb-user-menu');
    if (!menu) return;
    const open = menu.hidden;
    this.cerrarMenusTopbar(open ? 'tb-user-menu' : null);
    menu.hidden = !open;
    const btn = document.getElementById('tb-user');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  },

  togglePanelNotif(ev) {
    if (ev) {
      ev.preventDefault();
      ev.stopPropagation();
    }
    const panel = document.getElementById('tb-notif-panel');
    if (!panel) return;
    const open = panel.hidden;
    this.cerrarMenusTopbar(open ? 'tb-notif-panel' : null);
    panel.hidden = !open;
    const btn = document.getElementById('tb-notif');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) this.cargarPanelNotificaciones();
  },

  async cargarBadgeNotificaciones() {
    const badge = document.getElementById('tb-notif-badge');
    const token = localStorage.getItem('token');
    if (!badge || !token) return;
    try {
      const r = await fetch(`${this.getApi()}/api/notificaciones/?limit=1&solo_no_leidas=true`, {
        headers: { Authorization: 'Bearer ' + token },
        cache: 'no-store',
      });
      if (!r.ok) return;
      const d = await r.json();
      const n = Number(d.no_leidas || 0);
      if (n > 0) {
        badge.hidden = false;
        badge.textContent = n > 99 ? '99+' : String(n);
      } else {
        badge.hidden = true;
      }
    } catch (_) { /* ignore */ }
  },

  async cargarPanelNotificaciones() {
    const lista = document.getElementById('tb-notif-lista');
    const token = localStorage.getItem('token');
    if (!lista || !token) return;
    lista.innerHTML = `<div class="tb-notif-loading">${this.t('cargando')}</div>`;
    try {
      const r = await fetch(`${this.getApi()}/api/notificaciones/?limit=8&solo_no_leidas=false`, {
        headers: { Authorization: 'Bearer ' + token },
        cache: 'no-store',
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'error');
      const items = d.notificaciones || [];
      const n = Number(d.no_leidas || 0);
      const badge = document.getElementById('tb-notif-badge');
      if (badge) {
        if (n > 0) {
          badge.hidden = false;
          badge.textContent = n > 99 ? '99+' : String(n);
        } else badge.hidden = true;
      }
      if (!items.length) {
        lista.innerHTML = `<div class="tb-notif-empty">${this.t('tb_notif_vacias')}</div>`;
        return;
      }
      lista.innerHTML = items.map((n) => {
        const fecha = String(n.creado_en || '').replace('T', ' ').slice(0, 16);
        const titulo = String(n.titulo || '-').replace(/</g, '&lt;');
        const msg = String(n.mensaje || '').replace(/</g, '&lt;');
        const para = String(n.destinatario_label || this.etiquetaRol(n.destinatario) || '').replace(/</g, '&lt;');
        return `<button type="button" class="tb-notif-item${n.leida ? '' : ' unread'}" onclick="DiabCareNav.abrirNotif('${n.id}', ${n.leida ? 'true' : 'false'})">
          <div class="n-title">${titulo}</div>
          <div class="n-msg">${msg}</div>
          <div class="n-meta">${para ? `${this.t('tb_notif_para')}: ${para} · ` : ''}${fecha}</div>
        </button>`;
      }).join('');
    } catch (_) {
      lista.innerHTML = `<div class="tb-notif-empty">${this.t('tb_notif_error')}</div>`;
    }
  },

  async abrirNotif(id, yaLeida) {
    const token = localStorage.getItem('token');
    if (token && id && !yaLeida) {
      try {
        await fetch(`${this.getApi()}/api/notificaciones/${id}/leida`, {
          method: 'PATCH',
          headers: { Authorization: 'Bearer ' + token },
        });
      } catch (_) { /* ignore */ }
    }
    window.location.href = '/paginas/seguridad/notificaciones/index.html';
  },

  async marcarTodasNotif(ev) {
    if (ev) ev.stopPropagation();
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      await fetch(`${this.getApi()}/api/notificaciones/leer-todas`, {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token },
      });
      await this.cargarPanelNotificaciones();
      this.cargarBadgeNotificaciones();
    } catch (_) { /* ignore */ }
  },

  pintarAvatarTopbar(u) {
    const av = document.getElementById('tb-user-avatar');
    if (!av) return;
    const nombre = (u && u.nombre) || 'U';
    const letra = (nombre[0] || 'U').toUpperCase();
    const nameEl = document.getElementById('tb-user-name');
    const rolEl = document.getElementById('tb-user-rol');
    if (nameEl) nameEl.textContent = u.nombre || nombre;
    if (rolEl) rolEl.textContent = this.etiquetaRol(u.rol);
    const token = localStorage.getItem('token') || '';
    av.textContent = letra;
    if (!token) return;
    const bust = (u && u.foto_bust) || Date.now();
    fetch(`${this.getApi()}/api/auth/perfil/foto?t=${bust}`, {
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
      })
      .catch(() => { av.textContent = letra; });
  },

  toggleCategoria(btn) {
    if (this.estaColapsada()) return;
    btn.classList.toggle('open');
    const panel = btn.nextElementSibling;
    if (panel) panel.classList.toggle('open');
    btn.setAttribute('aria-expanded', btn.classList.contains('open') ? 'true' : 'false');
  },

  toggleModulo(h) {
    if (this.estaColapsada()) {
      const href = h.getAttribute('data-primary-href');
      if (href) window.location.href = href;
      return;
    }
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
      this.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
      return;
    }
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (u.idioma && !localStorage.getItem('diabcare_idioma')) {
      localStorage.setItem('diabcare_idioma', u.idioma === 'en' ? 'en' : 'es');
    }
    const nameEl = document.getElementById('userName');
    if (nameEl && u.nombre) {
      nameEl.textContent = u.nombre;
      const rolEl = document.getElementById('userRol');
      if (rolEl) rolEl.textContent = this.etiquetaRol(u.rol);
    }
    this.pintarAvatarSidebar(u);
    this.pintarAvatarTopbar(u);
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
    const key = String(rol || '').toLowerCase();
    const map = {
      administrador: 'rol_administrador',
      medico: 'rol_medico',
      enfermero: 'rol_enfermero',
      farmaceutico: 'rol_farmaceutico',
      analista: 'rol_analista',
    };
    if (map[key]) return this.t(map[key]);
    if (!key) return '-';
    return key.charAt(0).toUpperCase() + key.slice(1);
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
    window.location.replace('/');
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
    // replace: evita que "adelante" vuelva a una app sin token
    window.location.replace('/');
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
        self.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
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
        this.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
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
    return this.HOME_POR_ROL[rol] || '/paginas/clinico/analisis/informes/index.html';
  },

  guardRol(roles) {
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    if (!u.rol) { this.irLogin(); return; }
    if (!roles.includes(u.rol)) {
      window.location.replace(this.homeParaRol(u.rol));
    }
  },
};

window.toggle = (h) => DiabCareNav.toggle(h);
window.cerrarSesion = () => DiabCareNav.cerrarSesion();

/**
 * Con sesión activa, el botón "atrás" no debe sacar al login
 * (eso dejaba el login en historial y rompía el flujo del token).
 * Se define antes del boot para que el arranque sí lo invoque.
 */
DiabCareNav._protegerHistorialSesion = function _protegerHistorialSesion() {
  if (this._histProt) return;
  this._histProt = true;
  try {
    const t = localStorage.getItem('token');
    if (!t || this.tokenExpirado(t)) return;
    // Capa extra en el historial: "atrás" se queda en la misma página
    history.pushState({ diabcareApp: 1 }, '', location.href);
    window.addEventListener('popstate', () => {
      const tok = localStorage.getItem('token');
      if (!tok || this.tokenExpirado(tok)) return;
      history.pushState({ diabcareApp: 1 }, '', location.href);
    });
  } catch (_) { /* ignore */ }
};

(function bootSesionDiabCare() {
  try {
    const path = (window.location && window.location.pathname) || '';
    const enLogin = path === '/' || path === '/index.html'
      || path.includes('/seguridad/autenticacion');
    if (enLogin) return;
    DiabCareNav.instalarInterceptorAuth();
    DiabCareNav.iniciarVigilanciaSesion();
    DiabCareNav._protegerHistorialSesion();
  } catch (_) { /* ignore */ }
})();
