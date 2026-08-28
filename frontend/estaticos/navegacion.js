/**
 * DiabCare Hospital - navegación por departamentos y roles.
 * Matriz de acceso por rol (admin = supervisión total).
 * Auth: cookie httpOnly (JWT no se guarda en localStorage).
 */
(function _temaAlCargar() {
  try {
    const t = localStorage.getItem('diabcare_tema') || 'oscuro';
    document.documentElement.setAttribute('data-tema', t === 'claro' ? 'claro' : 'oscuro');
    const idi = localStorage.getItem('diabcare_idioma') || 'es';
    document.documentElement.setAttribute('lang', idi === 'en' ? 'en' : 'es');
  } catch (_) { /* ignore */ }
})();

/* No mostrar la base antigua mientras termina de cargar el chasis actual. */
(function _esperarEstiloActual() {
  const root = document.documentElement;
  root.classList.add('dc-style-pending');
  const guard = document.createElement('style');
  guard.id = 'dc-style-guard';
  guard.textContent = `
    html.dc-style-pending,
    html.dc-style-pending body { background:#1E2A2E; }
    html[data-tema="claro"].dc-style-pending,
    html[data-tema="claro"].dc-style-pending body { background:#E6E2DC; }
    html.dc-style-pending body.dc-uv { visibility:hidden !important; }
  `;
  (document.head || root).appendChild(guard);
  window.__dcStyleReady = () => {
    root.classList.remove('dc-style-pending');
    if (guard.parentNode) guard.parentNode.removeChild(guard);
  };
  window.setTimeout(window.__dcStyleReady, 350);
})();

/* Transición entre módulos sin superponer instantáneas de dos páginas. */
(function _coordinarNavegacionModulos() {
  let incomingModule = false;
  let incomingLabel = 'MÓDULO';
  try {
    const enInicio = /\/paginas\/inicio\//i.test(location.pathname || '');
    if (sessionStorage.getItem('dc_entry_splash') === '1') {
      document.documentElement.classList.add('dc-entry-splash-pending');
    }
    incomingModule = sessionStorage.getItem('dc_module_loading') === '1';
    if (enInicio) {
      incomingModule = false;
      sessionStorage.removeItem('dc_module_loading');
      document.documentElement.classList.remove('dc-module-loading-pending', 'dc-module-loading-leaving');
      document.documentElement.removeAttribute('data-dc-module-label');
    }
    if (incomingModule) {
      sessionStorage.removeItem('dc_module_loading');
      const root = document.documentElement;
      const label = String(document.title || 'Módulo')
        .replace(/^DiabCare\s*[-|]\s*/i, '')
        .trim() || 'Módulo';
      incomingLabel = label.toUpperCase();
      root.setAttribute('data-dc-module-label', label.toUpperCase());
      root.classList.add('dc-module-loading-pending');
    }
  } catch (_) { /* ignore */ }

  if (!incomingModule) {
    const limpiarOverlayViejo = () => document.getElementById('dc-module-loader-ui')?.remove();
    limpiarOverlayViejo();
    document.addEventListener('DOMContentLoaded', limpiarOverlayViejo, { once: true });
  }

  if (incomingModule) {
    const finishIncoming = () => {
      const overlay = document.createElement('div');
      overlay.id = 'dc-module-loader-ui';
      overlay.setAttribute('role', 'status');
      overlay.setAttribute('aria-live', 'polite');
      overlay.innerHTML = `
        <div class="dc-neon-loader">
          <div class="dc-neon-loader__pulse" aria-hidden="true">
            <span></span>
            <svg viewBox="0 0 96 64" focusable="false">
              <path d="M2 34h19l7-12 10 25 12-42 13 29h31" />
            </svg>
          </div>
          <div class="dc-neon-loader__copy">
            <span>DIABCARE / CARGA CLÍNICA</span>
            <strong></strong>
            <small>Sincronizando entorno médico</small>
          </div>
          <div class="dc-neon-loader__bars" aria-hidden="true">
            <i></i><i></i><i></i><i></i><i></i>
          </div>
        </div>`;
      const moduleName = overlay.querySelector('.dc-neon-loader__copy strong');
      if (moduleName) moduleName.textContent = incomingLabel;
      document.body.appendChild(overlay);
      window.setTimeout(() => {
        document.documentElement.classList.add('dc-module-loading-leaving');
        overlay.classList.add('is-leaving');
      }, 680);
      window.setTimeout(() => {
        overlay.remove();
        document.documentElement.classList.remove('dc-module-loading-pending', 'dc-module-loading-leaving');
        document.documentElement.removeAttribute('data-dc-module-label');
      }, 1000);
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', finishIncoming, { once: true });
    } else {
      finishIncoming();
    }
  }

  let leaving = false;
  window.DiabCareNavigate = (href) => {
    if (leaving) return true;
    let next;
    try { next = new URL(href, location.href); } catch (_) { return false; }
    if (next.origin !== location.origin || !next.pathname.startsWith('/paginas/')) return false;
    if (next.href === location.href) return false;
    leaving = true;
    try { sessionStorage.setItem('dc_module_loading', '1'); } catch (_) { /* ignore */ }
    location.assign(next.href);
    return true;
  };

  document.addEventListener('click', (event) => {
    if (leaving || event.defaultPrevented || event.button !== 0) return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!anchor || anchor.target || anchor.hasAttribute('download')) return;
    if (document.body && document.body.classList.contains('dc-auth')) return;
    let next;
    try { next = new URL(anchor.href, location.href); } catch (_) { return; }
    if (next.origin !== location.origin || !next.pathname.startsWith('/paginas/')) return;
    if (next.href === location.href) return;

    event.preventDefault();
    window.DiabCareNavigate(next.href);
  });
})();

/* Activa la transición entre documentos antes de pintar cualquier módulo. */
(function _habilitarTransicionModulos() {
  if (typeof document === 'undefined' || document.getElementById('dc-navigation-motion')) return;
  const style = document.createElement('style');
  style.id = 'dc-navigation-motion';
  style.textContent = `
    @view-transition { navigation: auto; }
    html::view-transition,
    html::view-transition-group(root),
    html::view-transition-image-pair(root),
    html::view-transition-old(root),
    html::view-transition-new(root) { background:#1E2A2E; }
    html[data-tema="claro"]::view-transition,
    html[data-tema="claro"]::view-transition-group(root),
    html[data-tema="claro"]::view-transition-image-pair(root),
    html[data-tema="claro"]::view-transition-old(root),
    html[data-tema="claro"]::view-transition-new(root) { background:#E6E2DC; }
  `;
  (document.head || document.documentElement).appendChild(style);
})();

/** Motion clínico (ECG / pulso) + pantallas de carga - siempre fresco */
(function _inyectarAnimaciones() {
  if (typeof document === 'undefined') return;
  if (document.getElementById('dc-animaciones-css')) return;
  if (document.querySelector('link[href*="animaciones.css"]')) return;
  const link = document.createElement('link');
  link.id = 'dc-animaciones-css';
  link.rel = 'stylesheet';
  link.href = '/estaticos/animaciones.css?v=contrast-1';
  (document.head || document.documentElement).appendChild(link);
})();

/** Interruptor clínico (tema + on/off) - pulso tipo SpO2, no holograma */
(function _inyectarHoloCss() {
  if (typeof document === 'undefined') return;
  let link = document.getElementById('dc-holo-css');
  if (!link) {
    link = document.createElement('link');
    link.id = 'dc-holo-css';
    link.rel = 'stylesheet';
    (document.head || document.documentElement).appendChild(link);
  }
  link.href = '/estaticos/holo-toggle.css?v=contrast-1';
})();

/** Chasis Uiverse (dock + cristal) - último CSS para ganar a lo anterior */
(function _inyectarUiverse() {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.add('dc-uv-html');
  const onBody = () => {
    if (!document.body || document.body.classList.contains('dc-auth')) return;
    document.body.classList.add('dc-uv');
  };
  onBody();
  document.addEventListener('DOMContentLoaded', onBody);
  let link = document.getElementById('dc-uiverse-css');
  if (!link) {
    const existing = document.querySelector('link[href*="uiverse-app.css"]');
    if (existing) {
      existing.id = 'dc-uiverse-css';
      existing.setAttribute('blocking', 'render');
      existing.addEventListener('load', window.__dcStyleReady, { once: true });
      existing.href = '/estaticos/uiverse-app.css?v=compact-37';
      if (existing.sheet) window.__dcStyleReady();
      return;
    }
    link = document.createElement('link');
    link.id = 'dc-uiverse-css';
    link.rel = 'stylesheet';
    link.setAttribute('blocking', 'render');
    link.addEventListener('load', window.__dcStyleReady, { once: true });
    link.addEventListener('error', window.__dcStyleReady, { once: true });
    (document.head || document.documentElement).appendChild(link);
  }
  link.href = '/estaticos/uiverse-app.css?v=compact-37';
})();

/** Pantalla de carga - fantasma del chasis (mismas radios que la app) */
(function _pantallaCarga() {
  let depth = 0;
  let hideTimer = null;
  let shownAt = 0;
  const MIN_MS = 480;

  const RUTAS_MODULO = [
    [/\/laboratorio\//i, 'Laboratorio'],
    [/\/pacientes\//i, 'Pacientes'],
    [/\/admisiones\//i, 'Admisiones'],
    [/\/habitaciones\//i, 'Habitaciones'],
    [/\/comorbilidades\//i, 'Comorbilidades'],
    [/\/urgencias\//i, 'Urgencias'],
    [/\/agenda\//i, 'Agenda médica'],
    [/\/mis_citas\//i, 'Mis citas'],
    [/\/registros_clinicos\//i, 'Consultas clínicas'],
    [/\/analisis\/diabetes\//i, 'Control de diabetes'],
    [/\/analisis\/estadisticas\//i, 'Estadísticas clínicas'],
    [/\/analisis\/informes\//i, 'Panel de análisis'],
    [/\/prediccion\//i, 'Predicción de diabetes'],
    [/\/reportes\//i, 'Reportes'],
    [/\/dataset\/generador\.html/i, 'Generador de datos'],
    [/\/dataset\//i, 'Dataset clínico'],
    [/\/pipeline_elt\//i, 'Pipeline ELT'],
    [/\/modelo_ml\//i, 'Modelo predictivo'],
    [/\/farmacia\//i, 'Farmacia'],
    [/\/facturacion\//i, 'Facturación'],
    [/\/recetas\//i, 'Recetas médicas'],
    [/\/rrhh\//i, 'Recursos humanos'],
    [/\/instrumental\//i, 'Instrumental clínico'],
    [/\/usuarios\//i, 'Usuarios'],
    [/\/perfil\//i, 'Perfil'],
    [/\/configuracion\//i, 'Configuración'],
    [/\/auditoria\//i, 'Auditoría'],
    [/\/notificaciones\//i, 'Notificaciones'],
    [/\/inicio\//i, 'Inicio'],
  ];

  function nombreModulo(path) {
    const p = path || (location.pathname || '');
    try {
      const tb = document.querySelector('.tb-page');
      const label = tb && String(tb.textContent || '').trim();
      if (label) return label;
    } catch (_) { /* ignore */ }
    for (const [re, name] of RUTAS_MODULO) {
      if (re.test(p)) return name;
    }
    return 'DiabCare';
  }

  function ensure() {
    let el = document.getElementById('dc-loading-screen');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'dc-loading-screen';
    el.hidden = true;
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    const row = () => `<div class="dc-sk-row" aria-hidden="true">
        <div class="dc-sk-bone dc-sk-ico"></div>
        <div class="dc-sk-row-lines">
          <div class="dc-sk-bone dc-sk-title"></div>
          <div class="dc-sk-bone dc-sk-value"></div>
        </div>
        <div class="dc-sk-bone dc-sk-badge"></div>
      </div>`;
    const stat = () => `<div class="dc-sk-stat" aria-hidden="true">
        <div class="dc-sk-bone dc-sk-label"></div>
        <div class="dc-sk-bone dc-sk-stat-val"></div>
      </div>`;
    el.innerHTML = `
      <div class="dc-sk-shell">
        <div class="dc-sk-topbar" aria-hidden="true">
          <div class="dc-sk-bone" style="width:28%;height:12px"></div>
          <div class="dc-sk-bone dc-sk-ico dc-sk-ico--sm" style="margin-left:auto"></div>
          <div class="dc-sk-bone dc-sk-ico dc-sk-ico--sm"></div>
        </div>
        <header class="dc-sk-mast">
          <div class="dc-sk-bone dc-sk-ico dc-sk-ico--hero"></div>
          <div class="dc-sk-mast-copy">
            <p class="dc-loading-title" id="dc-loading-title">Cargando</p>
            <p class="dc-loading-sub" id="dc-loading-sub">Preparando módulo…</p>
          </div>
        </header>
        <div class="dc-sk-stats">${stat()}${stat()}${stat()}${stat()}</div>
        <div class="dc-sk-cols">
          <section class="dc-sk-panel">
            <div class="dc-sk-panel-head">
              <div class="dc-sk-bone dc-sk-title" style="width:42%"></div>
              <div class="dc-sk-bone dc-sk-badge"></div>
            </div>
            ${row()}${row()}${row()}${row()}
          </section>
          <section class="dc-sk-panel">
            <div class="dc-sk-panel-head">
              <div class="dc-sk-bone dc-sk-title" style="width:36%"></div>
              <div class="dc-sk-bone dc-sk-badge"></div>
            </div>
            ${row()}${row()}${row()}
          </section>
        </div>
      </div>`;
    (document.body || document.documentElement).appendChild(el);
    return el;
  }

  function mostrar(msg, sub) {
    const el = ensure();
    const mod = nombreModulo();
    const t = document.getElementById('dc-loading-title');
    const s = document.getElementById('dc-loading-sub');
    if (t) {
      t.textContent = msg || ('Cargando ' + mod);
    }
    if (s) s.textContent = sub || (mod + ' - consultando datos…');
    clearTimeout(hideTimer);
    depth += 1;
    if (el.hidden) shownAt = Date.now();
    el.hidden = false;
  }

  function ocultar(force) {
    if (force) depth = 0;
    else depth = Math.max(0, depth - 1);
    if (depth > 0) return;
    const el = document.getElementById('dc-loading-screen');
    if (!el) return;
    const wait = Math.max(0, MIN_MS - (Date.now() - shownAt));
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (depth === 0) el.hidden = true;
    }, wait + 120);
  }

  window.DiabCareLoading = { mostrar, ocultar, ensure, nombreModulo };

  // Overlay del chasis SOLO al entrar tras login (no al cambiar de módulo)
  function splash() {
    const path = (location.pathname || '');
    const enLogin = path === '/' || path === '/index.html' || path.includes('/seguridad/autenticacion');
    if (enLogin) {
      try { document.body.classList.add('dc-auth'); } catch (_) { /* ignore */ }
      return;
    }
    let show = false;
    try {
      show = sessionStorage.getItem('dc_entry_splash') === '1';
      if (show) sessionStorage.removeItem('dc_entry_splash');
    } catch (_) { /* ignore */ }
    if (!show) return;
    mostrar('Bienvenido a DiabCare', 'Entrando a la plataforma…');
    setTimeout(() => {
      ocultar(true);
      document.documentElement.classList.remove('dc-entry-splash-pending');
    }, 1100);
  }
  if (document.body) splash();
  else document.addEventListener('DOMContentLoaded', splash);
})();

/** Skeleton con las mismas formas del chasis (cards 18px, stats 16px, filas 12px) */
(function _skeletonCargas() {
  const MIN_MS = 700;
  let _fetchDepth = 0;

  function tileHtml(i) {
    const delay = (i % 8) * 0.08;
    return `<article class="data-tile dc-sk-card" style="animation-delay:${delay}s" aria-hidden="true">
      <div class="data-tile-head">
        <div class="data-tile-avatar dc-sk-bone"></div>
        <div class="data-tile-head-text">
          <div class="dc-sk-bone dc-sk-title"></div>
          <div class="dc-sk-bone data-tile-badge dc-sk-badge"></div>
        </div>
      </div>
      <dl class="data-tile-meta">
        <div><div class="dc-sk-bone dc-sk-label"></div><div class="dc-sk-bone dc-sk-value"></div></div>
        <div><div class="dc-sk-bone dc-sk-label"></div><div class="dc-sk-bone dc-sk-value"></div></div>
        <div><div class="dc-sk-bone dc-sk-label"></div><div class="dc-sk-bone dc-sk-value"></div></div>
      </dl>
      <div class="data-tile-actions">
        <div class="dc-sk-bone dc-sk-btn"></div>
        <div class="dc-sk-bone dc-sk-btn"></div>
      </div>
    </article>`;
  }

  function htmlCards(n) {
    n = n || 8;
    let tiles = '';
    for (let i = 0; i < n; i++) tiles += tileHtml(i);
    return `<div class="data-grid dc-sk-grid" role="status" aria-busy="true" aria-label="Cargando">${tiles}</div>`;
  }

  function htmlList(n) {
    n = n || 4;
    let rows = '';
    for (let i = 0; i < n; i++) {
      rows += `<div class="dc-sk-row" style="animation-delay:${i * 0.1}s" aria-hidden="true">
        <div class="dc-sk-bone dc-sk-ico dc-sk-ico--sm"></div>
        <div class="dc-sk-row-lines">
          <div class="dc-sk-bone dc-sk-title"></div>
          <div class="dc-sk-bone dc-sk-value"></div>
        </div>
        <div class="dc-sk-bone dc-sk-badge"></div>
      </div>`;
    }
    return `<div class="dc-sk-list" role="status" aria-busy="true" aria-label="Cargando">${rows}</div>`;
  }

  function htmlStats(n) {
    n = n || 3;
    let cards = '';
    for (let i = 0; i < n; i++) {
      cards += `<div class="kpi-card dc-sk-stat" style="animation-delay:${i * 0.1}s" aria-hidden="true">
        <div class="dc-sk-bone dc-sk-label"></div>
        <div class="dc-sk-bone dc-sk-stat-val"></div>
        <div class="dc-sk-bone dc-sk-value" style="width:40%;margin-top:10px"></div>
      </div>`;
    }
    return cards;
  }

  function htmlKpis(n) {
    return htmlStats(n || 4);
  }

  function htmlPanel() {
    return `<div class="dc-sk-panel" role="status" aria-busy="true" aria-label="Cargando">
      <div class="dc-sk-panel-head">
        <div class="dc-sk-bone dc-sk-title" style="width:40%"></div>
        <div class="dc-sk-bone dc-sk-badge"></div>
      </div>
      <div class="dc-sk-bone dc-sk-chart"></div>
      <div class="dc-sk-row"><div class="dc-sk-bone dc-sk-value" style="width:70%"></div><div class="dc-sk-bone dc-sk-badge"></div></div>
      <div class="dc-sk-row"><div class="dc-sk-bone dc-sk-value" style="width:55%"></div><div class="dc-sk-bone dc-sk-badge"></div></div>
      <div class="dc-sk-row"><div class="dc-sk-bone dc-sk-value" style="width:62%"></div><div class="dc-sk-bone dc-sk-badge"></div></div>
    </div>`;
  }

  const CSS = `
@keyframes dc-sk-pulse{0%,100%{opacity:1}50%{opacity:.72}}
@keyframes dc-sk-shimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}
.loading.dc-loading-skeleton{
  display:block!important;width:100%!important;max-width:none!important;margin:0!important;
  padding:0!important;background:transparent!important;border:none!important;box-shadow:none!important;
  min-height:0!important;clip-path:none!important}
.loading.dc-loading-skeleton .spinner,.loading.dc-loading-skeleton .loading-dots{display:none!important}
.dash-row>.dc-sk-slot,.stats-grid>.dc-sk-slot,.stats-grid-compact>.dc-sk-slot,
.kpi-row>.dc-sk-slot,.metricas-grid>.dc-sk-slot,.uv-stats>.dc-sk-slot{display:contents!important}
.dc-sk-pulse-el{animation:dc-sk-pulse 1.6s ease-in-out infinite}
`;

  function ensureCss() {
    let s = document.getElementById('dc-skeleton-css');
    if (!s) {
      s = document.createElement('style');
      s.id = 'dc-skeleton-css';
      (document.head || document.documentElement).appendChild(s);
    }
    s.textContent = CSS;
  }

  function esTextoCarga(raw) {
    const t = String(raw || '').trim();
    if (!t) return true;
    if (/sin |error|no se pudo|sin coincidencias|sin url|sin archivos|sin sedes|sin recom/i.test(t)
        && !/cargando|buscando/i.test(t)) return false;
    return /cargando|buscando|preparando|seleccione|consultando/i.test(t);
  }

  function inferVariant(host) {
    if (!host) return 'cards';
    const id = String(host.id || '').toLowerCase();
    if (id === 'tablabody' || id.includes('tabla') || (host.closest && host.closest('.tabla-wrap'))) return 'cards';
    if (id === 'dwhnav' || id.includes('archivo') || id.includes('list') || id.includes('notif') || id.includes('audit')) return 'list';
    if (id.includes('sede') || id.includes('tip') || id.includes('recomend')) return 'panel';
    if (host.classList && host.classList.contains('panel')) return 'panel';
    if (host.classList && (host.classList.contains('stats-grid') || host.classList.contains('stat-card'))) return 'stats';
    if (host.classList && host.classList.contains('dash-row')) return 'kpis';
    if (host.querySelector && host.querySelector('.data-grid, .data-tile')) return 'cards';
    return 'list';
  }

  function markup(variant, host) {
    if (variant === 'cards') {
      const w = (host && host.clientWidth) || (typeof window !== 'undefined' ? window.innerWidth : 1200);
      const n = w > 1400 ? 8 : w > 900 ? 6 : 4;
      return htmlCards(n);
    }
    if (variant === 'stats') {
      const n = (host && host.querySelectorAll && host.querySelectorAll('.stat-card').length) || 3;
      return htmlStats(Math.max(3, n));
    }
    if (variant === 'kpis') return htmlKpis(4);
    if (variant === 'panel') return htmlPanel();
    return htmlList(5);
  }

  function paintExtras() {
    document.querySelectorAll(
      '.dash-row > .kpi-card, .stats-grid .stat-card, .kpi-val, .status-card, .status-val'
    ).forEach((el) => el.classList.add('dc-sk-pulse-el'));
  }

  function clearExtras() {
    document.querySelectorAll('.dc-sk-pulse-el').forEach((el) => el.classList.remove('dc-sk-pulse-el'));
    document.querySelectorAll('.dash-row > .kpi-card.dc-sk-stat, .stats-grid > .dc-sk-stat, .uv-stats > .dc-sk-stat').forEach((el) => el.remove());
    document.querySelectorAll('[data-dc-sk-hide="1"]').forEach((el) => {
      el.style.display = '';
      delete el.dataset.dcSkHide;
    });
    document.querySelectorAll('.dc-sk-slot').forEach((el) => el.remove());
    document.querySelectorAll('[data-dc-skeleton="1"]').forEach((el) => {
      // Restaura listado si el skeleton lo tapó (Ver/Descargar PDF, etc.)
      if (el._dcSkHtml != null) {
        const sigueSkeleton = !!(el.querySelector && el.querySelector('.dc-sk-bone, .dc-sk-grid, .dc-sk-tr, .dc-sk-list'));
        if (sigueSkeleton) el.innerHTML = el._dcSkHtml;
        delete el._dcSkHtml;
      }
      el.removeAttribute('aria-busy');
      el.classList.remove('dc-loading-skeleton', 'loading');
      delete el.dataset.dcSkeleton;
      delete el.dataset.dcSkVariant;
    });
  }

  function cuerpoLista(host) {
    if (!host) return null;
    const id = String(host.id || '').toLowerCase();
    if (id === 'tablabody' || id === 'tbody' || (host.tagName && host.tagName.toLowerCase() === 'tbody')) {
      return host;
    }
    if (host.querySelector) {
      return host.querySelector('#tablaBody, #tbody')
        || (host.classList && host.classList.contains('tabla-wrap') ? host.querySelector('tbody') : null);
    }
    return null;
  }

  function htmlTableRows(n, cols) {
    const c = Math.max(1, cols || 5);
    let rows = '';
    for (let i = 0; i < n; i += 1) {
      let cells = '';
      for (let j = 0; j < c; j += 1) {
        const w = 52 + ((i + j) % 4) * 11;
        cells += `<td><div class="dc-sk-bone" style="height:11px;width:${w}%;margin:10px 6px"></div></td>`;
      }
      rows += `<tr class="dc-sk-tr" aria-hidden="true" style="animation-delay:${i * 0.08}s">${cells}</tr>`;
    }
    return rows;
  }

  function tieneListadoReal(el) {
    if (!el || !el.querySelector) return false;
    if (el.querySelector('.dc-sk-bone, .dc-sk-grid, .dc-sk-tr, .dc-sk-card, .dc-sk-list')) return false;
    return !!(el.querySelector('.data-tile, .data-grid > .data-tile, table tbody tr'));
  }

  function paintTablaCuerpo(tb) {
    if (!tb) return null;
    if (tieneListadoReal(tb)) return tb;
    ensureCss();
    // Guarda el HTML real para restaurarlo al terminar el fetch (p. ej. Ver PDF)
    if (tb._dcSkHtml == null) tb._dcSkHtml = tb.innerHTML;
    const table = tb.closest && tb.closest('table');
    const cols = table ? table.querySelectorAll('thead th').length : 5;
    tb.classList.add('dc-loading-skeleton');
    tb.dataset.dcSkeleton = '1';
    tb.dataset.dcSkVariant = tb.tagName && tb.tagName.toLowerCase() === 'tbody' ? 'rows' : 'cards';
    tb.setAttribute('aria-busy', 'true');
    tb.setAttribute('aria-label', 'Cargando');
    if (tb.tagName && tb.tagName.toLowerCase() === 'tbody') {
      tb.innerHTML = htmlTableRows(6, cols || 5);
    } else {
      tb.innerHTML = markup('cards', tb);
    }
    tb._dcSkAt = Date.now();
    paintExtras();
    return tb;
  }

  function paint(el, variant) {
    if (!el || !el.setAttribute) return;
    ensureCss();
    const v = variant || inferVariant(el);
    el.classList.add('loading', 'dc-loading-skeleton');
    el.dataset.dcSkeleton = '1';
    el.dataset.dcSkVariant = v;
    el.setAttribute('role', 'status');
    el.setAttribute('aria-busy', 'true');
    el.setAttribute('aria-label', 'Cargando');
    el.innerHTML = markup(v, el);
    el._dcSkAt = Date.now();
  }

  /** Oculta hijos (salvo keepSel) y pone un slot skeleton encima - no rompe IDs al terminar. */
  function paintKeepChildren(host, html, keepSel) {
    if (!host) return null;
    ensureCss();
    if (host.querySelector(':scope > .dc-sk-slot')) {
      host._dcSkAt = Date.now();
      return host;
    }
    const keep = keepSel ? host.querySelector(keepSel) : null;
    Array.from(host.children).forEach((ch) => {
      if (keep && ch === keep) return;
      if (ch.classList && ch.classList.contains('dc-sk-slot')) {
        ch.remove();
        return;
      }
      ch.dataset.dcSkHide = '1';
      ch.style.display = 'none';
    });
    const slot = document.createElement('div');
    slot.className = 'dc-sk-slot loading dc-loading-skeleton';
    slot.dataset.dcSkeleton = '1';
    slot.setAttribute('role', 'status');
    slot.setAttribute('aria-busy', 'true');
    slot.setAttribute('aria-label', 'Cargando');
    slot.innerHTML = html;
    slot._dcSkAt = Date.now();
    host.appendChild(slot);
    host._dcSkAt = Date.now();
    return host;
  }

  function paintPanelKeepTitle(host) {
    return paintKeepChildren(host, htmlPanel(), ':scope > .panel-title');
  }

  function esHostKpi(host) {
    if (!host || !host.classList) return false;
    return host.classList.contains('dash-row')
      || host.classList.contains('stats-grid')
      || host.classList.contains('stats-grid-compact')
      || host.classList.contains('kpi-row')
      || host.classList.contains('metricas-grid')
      || host.id === 'kpisCaja'
      || host.id === 'statsTop'
      || host.id === 'row-kpis';
  }

  function paintInto(host) {
    if (!host) return null;
    // Escritorio de inicio: nunca vaciar ni tapar
    if (host.id === 'home-grid' || (host.classList && host.classList.contains('dc-home'))) return null;
    if (host.closest && host.closest('.dc-home')) return null;
    if (host.querySelector && host.querySelector('.dc-home')) return null;
    if (tieneListadoReal(host)) return host;
    ensureCss();
    // Nunca vaciar el card/wrap entero: ir al cuerpo de lista (#tablaBody / #tbody)
    if (host.classList && (host.classList.contains('tabla-card') || host.classList.contains('tabla-wrap'))) {
      const tb = cuerpoLista(host);
      if (tb) return paintTablaCuerpo(tb);
      // Card sin cuerpo de lista (p. ej. #boxHallazgos, que lleva un <ul>):
      // ocultar sin destruir. Si se cae al innerHTML='' del final, se borran
      // nodos que el modulo busca luego por id y su render explota.
      paintKeepChildren(host, htmlPanel());
      paintExtras();
      return host;
    }
    if (host.id === 'tablaBody' || host.id === 'tbody' || (host.tagName && host.tagName.toLowerCase() === 'tbody')) {
      return paintTablaCuerpo(host);
    }
    if (esHostKpi(host)) {
      const cards = host.querySelectorAll(':scope > .kpi-card, :scope > .stat-card, :scope > .uv-stat');
      if (cards.length) {
        cards.forEach((el) => el.classList.add('dc-sk-pulse-el'));
        host._dcSkAt = Date.now();
        return host;
      }
      const n = Math.max(3, host.children.length || 4);
      host.insertAdjacentHTML('beforeend', htmlKpis(n));
      host.dataset.dcSkeleton = '1';
      host._dcSkAt = Date.now();
      return host;
    }
    if (host.classList && host.classList.contains('panel')) {
      // Si el panel ya tiene tabla, skeleton solo en el cuerpo - no ocultar todo el panel
      const tb = cuerpoLista(host);
      if (tb) return paintTablaCuerpo(tb);
      paintPanelKeepTitle(host);
      paintExtras();
      return host;
    }
    if (host.classList && (host.classList.contains('pred-card') || host.classList.contains('pipe-card'))) {
      paintKeepChildren(host, htmlPanel());
      paintExtras();
      return host;
    }
    const variant = inferVariant(host);
    if (variant === 'cards' || host.id === 'tablaBody' || (host.classList && host.classList.contains('tabla-wrap'))) {
      const target = cuerpoLista(host) || host;
      return paintTablaCuerpo(target);
    }
    // Contenedores de lista / nav / archivos / bandejas
    if (
      host.id === 'dwhNav' || host.id === 'archivos-list' || host.id === 'archivosList'
      || host.id === 'lista' || host.id === 'factoresList'
      || /list|notif|audit|consult|archivo/i.test(host.id || '')
    ) {
      host.classList.add('dc-loading-skeleton');
      host.dataset.dcSkeleton = '1';
      host.innerHTML = markup('list', host);
      host._dcSkAt = Date.now();
      paintExtras();
      return host;
    }
    if (host.id === 'sedes-box' || host.id === 'tips-box' || host.id === 'metricasBox' || host.id === 'predResultado') {
      host.classList.add('dc-loading-skeleton');
      host.dataset.dcSkeleton = '1';
      host.innerHTML = markup('panel', host);
      host._dcSkAt = Date.now();
      paintExtras();
      return host;
    }
    let box = host.classList && host.classList.contains('loading') ? host : null;
    if (!box && host.querySelector) box = host.querySelector(':scope > .loading');
    if (!box) {
      box = document.createElement('div');
      box.className = 'loading dc-loading-skeleton';
      host.innerHTML = '';
      host.appendChild(box);
    }
    paint(box, variant === 'cards' ? 'list' : variant);
    paintExtras();
    return box;
  }

  function enrich(root) {
    ensureCss();
    (root || document).querySelectorAll('.loading').forEach((el) => {
      if (el.dataset.dcSkeleton === '1') return;
      if (el.classList.contains('dc-sk-slot')) return;
      el.querySelectorAll('.spinner, .loading-dots').forEach((n) => n.remove());
      const raw = String(el.textContent || '').trim();
      if (!esTextoCarga(raw)) return;
      const host = el.parentElement && el.parentElement.id === 'tablaBody' ? el.parentElement : el;
      if (host.id === 'tablaBody') paintInto(host);
      else paint(el, inferVariant(el.parentElement || el));
    });
  }

  async function waitFrom(el, minMs) {
    const t0 = (el && el._dcSkAt) || Date.now();
    const w = Math.max(0, (minMs == null ? MIN_MS : minMs) - (Date.now() - t0));
    if (w) await new Promise((r) => setTimeout(r, w));
  }

  function targetsParaFetch() {
    const out = [];
    const add = (el) => {
      if (!el || out.indexOf(el) >= 0) return;
      if (el.closest && el.closest('aside.sidebar, .sidebar, .modal, .modal-overlay, #dc-loading-screen, .tb-notif-panel, #tb-notif-lista')) return;
      out.push(el);
    };

    add(document.getElementById('tablaBody'));
    add(document.getElementById('tbody'));
    document.querySelectorAll('.tabla-wrap').forEach((w) => add(cuerpoLista(w) || w));

    [
      'sedes-box', 'tips-box', 'archivos-list', 'archivosList', 'dwhNav', 'exp-consultas',
      'notifList', 'auditBody', 'metricasBox', 'predResultado', 'lista', 'factoresList',
      'statsTop', 'kpisCaja', 'row-kpis', 'solicitudesBody', 'sesionesAdminBody', 'sesionesBody',
    ].forEach((id) => add(document.getElementById(id)));

    document.querySelectorAll(
      '[id$="Body"], [id$="-box"], [id$="-list"], [id$="List"], [id$="-nav"], [id$="Nav"]'
    ).forEach(add);

    document.querySelectorAll(
      '.dash-row, .stats-grid, .stats-grid-compact, .kpi-row, .metricas-grid'
    ).forEach(add);

    document.querySelectorAll('.panel').forEach((p) => {
      // Evita tapar paneles de formulario/preview; solo listas/tablas
      if (p.classList.contains('panel-preview') || p.classList.contains('panel-form')) return;
      if (p.querySelector('#tablaBody, #tbody, .tabla-wrap, .data-grid, .loading')) add(p);
    });

    document.querySelectorAll('.pred-card, .pipe-card').forEach(add);

    document.querySelectorAll('.loading').forEach((el) => {
      if (el.closest && el.closest('#tablaBody')) return add(document.getElementById('tablaBody'));
      if (el.closest && el.closest('.tb-notif-panel, #tb-notif-lista')) return;
      if (esTextoCarga(el.textContent) || el.dataset.dcSkeleton === '1') add(el);
    });

    return out;
  }

  function debeSkeletonFetch(url, opts) {
    const method = String((opts && opts.method) || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'POST') return false;
    if (method === 'POST' && !/\/api\/(pipeline|dataset|prediccion|modelo)/i.test(url)) return false;
    if (!/\/api\//i.test(url)) return false;
    if (/\/api\/auth\//i.test(url)) return false;
    if (/\/api\/health\b/i.test(url)) return false;
    if (/suggest|typeahead|autocomplete|\/foto/i.test(url)) return false;
    if (/[?&]q=/i.test(url) && /\/api\/(pacientes|medicamentos|usuarios)\//i.test(url)) return false;
    if (opts && (opts.silent || opts.dcSilent || opts.skeleton === false)) return false;
    // Escritorio / inicio: no tapar las acciones del día
    if (/\/paginas\/inicio\//i.test(location.pathname || '')) return false;
    if (document.querySelector('.dc-home')) return false;
    // Badge / panel del topbar (no son carga de módulo)
    if (/\/api\/notificaciones\//i.test(url) && !/\/paginas\/seguridad\/notificaciones\//i.test(location.pathname || '')) {
      return false;
    }
    // Ver/Descargar un PDF concreto: no tapar el historial
    // Lista = /api/reportes/  |  Archivo = /api/reportes/nombre.pdf
    if (/\/api\/reportes\/[^/?#]+/i.test(url)
        && !/\/api\/reportes\/(verificar|historial|vaciar-historial)\b/i.test(url)) {
      return false;
    }
    // Vista previa / blob de verificación pública
    if (/\/api\/reportes\/verificar\/[^/]+\/pdf/i.test(url)) return false;
    return !!document.querySelector('.main .content, #diabcare-sidebar, .sidebar');
  }

  function paintAllForFetch() {
    ensureCss();
    // Nunca skeleton sobre el escritorio
    if (document.querySelector('.dc-home') || /\/paginas\/inicio\//i.test(location.pathname || '')) return;
    const hosts = targetsParaFetch();
    if (!hosts.length) {
      const fallback = document.querySelector(
        '.tabla-card .tabla-wrap, .tabla-card, .content .panel, .content .dash-row'
      );
      if (fallback && !fallback.closest('.dc-home')) hosts.push(fallback);
    }
    const seen = new Set();
    let painted = 0;
    hosts.forEach((h) => {
      if (!h || seen.has(h)) return;
      if (h.closest && h.closest('.dc-home')) return;
      seen.add(h);
      try {
        paintInto(h);
        painted += 1;
      } catch (_) { /* ignore */ }
    });
    // Sin fallback a .main .content: destruía el escritorio y otras páginas
    paintExtras();
  }

  // Un skeleton nunca debe sobrevivir a su petición. Si una llamada no cierra
  // el suyo (error de red, promesa que no resuelve, navegación a media carga),
  // _fetchDepth queda en >0 y clearExtras() ya no vuelve a ejecutarse nunca:
  // la tarjeta se queda tapada de forma permanente y ninguna llamada posterior
  // la recupera. Este plazo máximo garantiza que la UI siempre vuelva.
  // Holgado a proposito: entrenar el modelo o generar dataset son operaciones
  // legitimamente largas. Esto no es un tiempo de espera, es el ultimo recurso
  // para que la interfaz nunca quede tapada de forma permanente.
  const SK_MAX_MS = 20000;
  let _skDesde = 0;

  function _forzarLimpieza() {
    _fetchDepth = 0;
    _skDesde = 0;
    try { clearExtras(); } catch (_) { /* ignore */ }
  }

  function beginFetchSkeleton() {
    _fetchDepth += 1;
    if (_fetchDepth === 1) {
      _skDesde = Date.now();
      paintAllForFetch();
    }
    return Date.now();
  }

  async function endFetchSkeleton(skAt, minMs) {
    // Descontar ANTES de la espera cosmética: si el temporizador no llega a
    // dispararse (navegación, pestaña suspendida), el contador ya quedó bien y
    // la siguiente llamada puede limpiar. Descontando después, esa ventana
    // dejaba el contador alto y el skeleton no se retiraba nunca más.
    _fetchDepth = Math.max(0, _fetchDepth - 1);
    const wait = Math.max(0, (minMs == null ? MIN_MS : minMs) - (Date.now() - (skAt || Date.now())));
    if (wait) await new Promise((r) => setTimeout(r, wait));
    if (_fetchDepth === 0) {
      _skDesde = 0;
      try { clearExtras(); } catch (_) { /* ignore */ }
    }
  }

  setInterval(() => {
    if (_fetchDepth > 0 && _skDesde && (Date.now() - _skDesde) > SK_MAX_MS) _forzarLimpieza();
  }, 2000);

  window.DiabCareSkeleton = {
    paint, paintInto,     paintAllForFetch, enrich, waitFrom, MIN_MS, clearExtras,
    debeSkeletonFetch, targetsParaFetch, inferVariant,
    cuerpoLista, paintTablaCuerpo,
    beginFetchSkeleton, endFetchSkeleton,
    htmlCards, htmlList, htmlStats, htmlKpis, htmlPanel,
  };
  window.DiabCareEnrichLoading = enrich;

  function boot() {
    ensureCss();
    enrich();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  try {
    let moTimer = null;
    const mo = new MutationObserver(() => {
      if (moTimer) return;
      moTimer = setTimeout(() => {
        moTimer = null;
        enrich();
      }, 50);
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  } catch (_) { /* ignore */ }
})();

/** Compat: páginas viejas leen localStorage.token; nunca devolvemos el JWT real. */
(function _authLocalStorageShim() {
  if (typeof window === 'undefined' || window.__dcAuthShim) return;
  window.__dcAuthShim = true;
  try {
    const ls = window.localStorage;
    const _get = ls.getItem.bind(ls);
    const _set = ls.setItem.bind(ls);
    const _remove = ls.removeItem.bind(ls);
    const _clear = ls.clear.bind(ls);
    const legacy = _get('token');
    if (legacy && legacy !== 'sesion' && String(legacy).includes('.')) {
      try { _remove('token'); } catch (_) { /* ignore */ }
    }
    ls.getItem = function (key) {
      if (key === 'token') {
        try {
          if (sessionStorage.getItem('dc_sesion_ok') === '1') return 'sesion';
        } catch (_) { /* ignore */ }
        return null;
      }
      return _get(key);
    };
    ls.setItem = function (key, value) {
      if (key === 'token') {
        try {
          if (value) sessionStorage.setItem('dc_sesion_ok', '1');
          else sessionStorage.removeItem('dc_sesion_ok');
        } catch (_) { /* ignore */ }
        try { _remove('token'); } catch (_) { /* ignore */ }
        return;
      }
      return _set(key, value);
    };
    ls.removeItem = function (key) {
      if (key === 'token') {
        try { sessionStorage.removeItem('dc_sesion_ok'); } catch (_) { /* ignore */ }
      }
      return _remove(key);
    };
    ls.clear = function () {
      try { sessionStorage.removeItem('dc_sesion_ok'); } catch (_) { /* ignore */ }
      return _clear();
    };
  } catch (_) { /* ignore */ }
})();

window.DiabCareNav = {
  getApi() {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    const { protocol, hostname, port, origin } = window.location;
    // El mismo FastAPI sirve el frontend y la API, asi que el origen actual
    // siempre es el correcto. Clavar el puerto 8000 rompia la app entera al
    // levantarla en cualquier otro puerto (o detras de un proxy).
    if (protocol === 'http:' || protocol === 'https:') return origin;
    const host = hostname && hostname !== '' ? hostname : 'localhost';
    return `http://${host}:${port || '8000'}`;
  },
  get API() { return this.getApi(); },

  /** Entrada: escritorio por rol (no un módulo suelto). */
  HOME_POR_ROL: {
    administrador: '/paginas/inicio/index.html',
    medico: '/paginas/inicio/index.html',
    enfermero: '/paginas/inicio/index.html',
    farmaceutico: '/paginas/inicio/index.html',
    analista: '/paginas/inicio/index.html',
  },

  /** Nombre único mostrado en pestaña, barra superior y encabezado. */
  NOMBRES_RUTA: [
    [/\/analisis\/estadisticas\//i, 'Estadísticas clínicas'],
    [/\/analisis\/diabetes\//i, 'Control de diabetes'],
    [/\/analisis\/informes\//i, 'Panel de análisis'],
    [/\/dataset\/generador\.html/i, 'Generador de datos'],
    [/\/registros_clinicos\//i, 'Consultas clínicas'],
    [/\/pipeline_elt\//i, 'Pipeline ELT'],
    [/\/modelo_ml\//i, 'Modelo predictivo'],
    [/\/instrumental\//i, 'Instrumental clínico'],
    [/\/comorbilidades\//i, 'Comorbilidades'],
    [/\/habitaciones\//i, 'Habitaciones'],
    [/\/admisiones\//i, 'Admisiones'],
    [/\/mis_citas\//i, 'Mis citas'],
    [/\/pacientes\//i, 'Pacientes'],
    [/\/agenda\//i, 'Agenda médica'],
    [/\/urgencias\//i, 'Urgencias'],
    [/\/laboratorio\//i, 'Laboratorio'],
    [/\/prediccion\//i, 'Predicción de diabetes'],
    [/\/reportes\//i, 'Reportes'],
    [/\/recetas\//i, 'Recetas médicas'],
    [/\/farmacia\//i, 'Farmacia'],
    [/\/facturacion\//i, 'Facturación'],
    [/\/rrhh\//i, 'Recursos humanos'],
    [/\/dataset\//i, 'Dataset clínico'],
    [/\/usuarios\//i, 'Usuarios'],
    [/\/notificaciones\//i, 'Notificaciones'],
    [/\/auditoria\//i, 'Auditoría'],
    [/\/configuracion\//i, 'Configuración'],
    [/\/perfil\//i, 'Mi perfil'],
    [/\/inicio\//i, 'Inicio'],
  ],

  /** Familia visual de cada pantalla. Inicio queda fuera del rediseño. */
  LAYOUT_RUTAS: [
    [/\/habitaciones\//i, 'board'],
    [/\/(laboratorio|farmacia|facturacion|rrhh|configuracion)\//i, 'tabs'],
    [/\/(analisis|prediccion|reportes|dataset|pipeline_elt|modelo_ml)\//i, 'insights'],
    [/\/(pacientes|agenda|mis_citas|registros_clinicos|admisiones|urgencias|instrumental|comorbilidades|recetas|usuarios|notificaciones|auditoria|perfil)\//i, 'records'],
  ],

  /** Icono del rail por categoría */
  ICONO_AREA: {
    clinico: 'estetoscopio',
    hospitalizacion: 'admisiones',
    farmacia_rx: 'farmacia',
    negocio: 'facturacion',
    analisis: 'analisis',
    datos: 'laboratorio',
    gobierno: 'configuracion',
    seguridad: 'lock',
  },

  /**
   * Escritorio por rol: pocas acciones grandes del día.
   * href + labelKey + icon (DiabCareIcons) + modulo (para filtrar ACCESO).
   */
  ESCRITORIO_POR_ROL: {
    administrador: [
      { modulo: 'pacientes', href: '/paginas/clinico/pacientes/index.html', labelKey: 'home_pacientes', icon: 'pacientes', hintKey: 'home_pacientes_h' },
      { modulo: 'citas', href: '/paginas/clinico/agenda/index.html', labelKey: 'home_agenda', icon: 'citas', hintKey: 'home_agenda_h' },
      { modulo: 'analisis', href: '/paginas/clinico/analisis/informes/index.html', labelKey: 'home_panel', icon: 'panel', hintKey: 'home_panel_h' },
      { modulo: 'facturacion', href: '/paginas/negocio/facturacion/index.html', labelKey: 'home_caja', icon: 'facturacion', hintKey: 'home_caja_h' },
      { modulo: 'farmacia', href: '/paginas/negocio/farmacia/index.html', labelKey: 'home_farmacia', icon: 'farmacia', hintKey: 'home_farmacia_h' },
      { modulo: 'reportes', href: '/paginas/clinico/reportes/index.html', labelKey: 'home_pdf', icon: 'pdf', hintKey: 'home_pdf_h' },
    ],
    medico: [
      { modulo: 'mis_citas', href: '/paginas/clinico/mis_citas/index.html', labelKey: 'home_mis_citas', icon: 'mis_citas', hintKey: 'home_mis_citas_h' },
      { modulo: 'pacientes', href: '/paginas/clinico/pacientes/index.html', labelKey: 'home_pacientes', icon: 'pacientes', hintKey: 'home_pacientes_h' },
      { modulo: 'registros', href: '/paginas/clinico/registros_clinicos/index.html', labelKey: 'home_consulta', icon: 'registros', hintKey: 'home_consulta_h' },
      { modulo: 'laboratorio', href: '/paginas/clinico/laboratorio/index.html', labelKey: 'home_lab', icon: 'laboratorio', hintKey: 'home_lab_h' },
      { modulo: 'prediccion', href: '/paginas/clinico/prediccion/index.html', labelKey: 'home_riesgo', icon: 'prediccion', hintKey: 'home_riesgo_h' },
    ],
    enfermero: [
      { modulo: 'pacientes', href: '/paginas/clinico/pacientes/index.html', labelKey: 'home_pacientes', icon: 'pacientes', hintKey: 'home_pacientes_h' },
      { modulo: 'admisiones', href: '/paginas/clinico/admisiones/index.html', labelKey: 'home_admision', icon: 'admisiones', hintKey: 'home_admision_h' },
      { modulo: 'citas', href: '/paginas/clinico/agenda/index.html', labelKey: 'home_agenda', icon: 'citas', hintKey: 'home_agenda_h' },
      { modulo: 'urgencias', href: '/paginas/clinico/urgencias/index.html', labelKey: 'home_urgencias', icon: 'urgencias', hintKey: 'home_urgencias_h' },
      { modulo: 'laboratorio', href: '/paginas/clinico/laboratorio/index.html', labelKey: 'home_lab', icon: 'laboratorio', hintKey: 'home_lab_h' },
    ],
    farmaceutico: [
      { modulo: 'farmacia', href: '/paginas/negocio/farmacia/index.html', labelKey: 'home_dispensar', icon: 'farmacia', hintKey: 'home_dispensar_h' },
      { modulo: 'facturacion', href: '/paginas/negocio/facturacion/index.html', labelKey: 'home_caja', icon: 'facturacion', hintKey: 'home_caja_h' },
      { modulo: 'pacientes', href: '/paginas/clinico/pacientes/index.html', labelKey: 'home_pacientes', icon: 'pacientes', hintKey: 'home_pacientes_h' },
      { modulo: 'analisis', href: '/paginas/clinico/analisis/informes/index.html', labelKey: 'home_panel', icon: 'panel', hintKey: 'home_panel_h' },
    ],
    analista: [
      { modulo: 'analisis', href: '/paginas/clinico/analisis/informes/index.html', labelKey: 'home_panel', icon: 'panel', hintKey: 'home_panel_h' },
      { modulo: 'analisis', href: '/paginas/clinico/analisis/estadisticas/index.html', labelKey: 'estadisticas', icon: 'stats', hintKey: 'sub_estadisticas' },
      { modulo: 'analisis', href: '/paginas/clinico/analisis/diabetes/index.html', labelKey: 'calidad_dm', icon: 'analisis', hintKey: 'sub_calidad' },
      { modulo: 'dataset', href: '/paginas/datos/dataset/index.html', labelKey: 'home_dataset', icon: 'dataset', hintKey: 'home_dataset_h' },
      { modulo: 'pipeline', href: '/paginas/datos/pipeline_elt/index.html', labelKey: 'home_elt', icon: 'pipeline', hintKey: 'home_elt_h' },
      { modulo: 'modelo', href: '/paginas/datos/modelo_ml/index.html', labelKey: 'home_modelo', icon: 'modelo', hintKey: 'home_modelo_h' },
      { modulo: 'reportes', href: '/paginas/clinico/reportes/index.html', labelKey: 'home_pdf', icon: 'pdf', hintKey: 'home_pdf_h' },
    ],
  },

  MODULOS_NAVEGABLES: [
    'pacientes', 'admisiones', 'urgencias', 'citas', 'mis_citas', 'registros',
    'laboratorio', 'comorbilidades', 'instrumental',
    'recetas', 'farmacia', 'facturacion', 'rrhh',
    'analisis', 'prediccion', 'reportes',
    'dataset', 'pipeline', 'modelo',
    'usuarios', 'auditoria', 'configuracion', 'notificaciones',
  ],

  MODULOS_PROXIMO: [],

  /**
   * Menú por FUNCIÓN, en orden de flujo hospitalario (no alfabético).
   * Atención → farmacia/caja → lectura → datos → gobierno.
   * Visibilidad real = ACCESO[rol].
   */
  CATEGORIAS: [
    {
      id: 'clinico',
      labelKey: 'cat_clinico',
      items: [
        { modulo: 'pacientes', modulos: ['pacientes', 'citas', 'mis_citas', 'registros', 'comorbilidades'], label: 'Atención del paciente', icon: 'pacientes', subs: [
          { modulo: 'pacientes', href: '/paginas/clinico/pacientes/index.html', labelKey: 'sub_expedientes' },
          { modulo: 'citas', href: '/paginas/clinico/agenda/index.html', labelKey: 'sub_agenda' },
          { modulo: 'mis_citas', href: '/paginas/clinico/mis_citas/index.html', labelKey: 'sub_turnos' },
          { modulo: 'registros', href: '/paginas/clinico/registros_clinicos/index.html', labelKey: 'sub_registro' },
          { modulo: 'comorbilidades', href: '/paginas/clinico/comorbilidades/index.html', labelKey: 'sub_complicaciones' },
        ]},
        { modulo: 'urgencias', labelKey: 'urgencias', subs: [
          { href: '/paginas/clinico/urgencias/index.html', labelKey: 'sub_triage' },
        ]},
        { modulo: 'laboratorio', labelKey: 'laboratorio', subs: [
          { href: '/paginas/clinico/laboratorio/index.html', labelKey: 'sub_ordenes' },
        ]},
      ],
    },
    {
      id: 'hospitalizacion',
      labelKey: 'cat_hospitalizacion',
      items: [
        { modulo: 'habitaciones', modulos: ['admisiones', 'habitaciones', 'instrumental'], label: 'Gestión hospitalaria', icon: 'admisiones', subs: [
          { modulo: 'admisiones', href: '/paginas/clinico/admisiones/index.html', labelKey: 'sub_ingresos' },
          { modulo: 'habitaciones', href: '/paginas/clinico/habitaciones/index.html', labelKey: 'sub_mapa_camas' },
          { modulo: 'instrumental', href: '/paginas/clinico/instrumental/index.html', labelKey: 'sub_instrumental' },
        ]},
      ],
    },
    {
      id: 'farmacia_rx',
      labelKey: 'cat_farmacia_rx',
      items: [
        { modulo: 'farmacia', labelKey: 'farmacia', subs: [
          { href: '/paginas/negocio/farmacia/index.html', labelKey: 'sub_dispensacion' },
        ]},
      ],
    },
    {
      id: 'negocio',
      labelKey: 'cat_negocio',
      items: [
        { modulo: 'facturacion', modulos: ['farmacia', 'facturacion', 'rrhh'], label: 'Gestión administrativa', icon: 'facturacion', subs: [
          { modulo: 'facturacion', href: '/paginas/negocio/facturacion/index.html', labelKey: 'sub_facturacion' },
          { modulo: 'farmacia', href: '/paginas/negocio/farmacia/index.html?area=gestion', labelKey: 'sub_operaciones' },
          { modulo: 'rrhh', href: '/paginas/negocio/rrhh/index.html', labelKey: 'sub_costeo' },
        ]},
      ],
    },
    {
      id: 'analisis',
      labelKey: 'cat_analisis',
      items: [
        { modulo: 'analisis', modulos: ['analisis', 'reportes'], label: 'Análisis clínico', icon: 'analisis', subs: [
          { modulo: 'analisis', href: '/paginas/clinico/analisis/informes/index.html', labelKey: 'sub_panel' },
          { modulo: 'analisis', href: '/paginas/clinico/analisis/estadisticas/index.html', labelKey: 'sub_estadisticas' },
          { modulo: 'reportes', href: '/paginas/clinico/reportes/index.html', labelKey: 'sub_pdf' },
        ]},
      ],
    },
    {
      id: 'datos',
      labelKey: 'cat_datos',
      items: [
        { modulo: 'dataset', modulos: ['dataset', 'pipeline', 'modelo', 'prediccion'], label: 'Plataforma de datos', icon: 'dataset', subs: [
          { modulo: 'dataset', href: '/paginas/datos/dataset/index.html', labelKey: 'sub_hechos' },
          { modulo: 'pipeline', href: '/paginas/datos/pipeline_elt/index.html', labelKey: 'sub_estado' },
          // Un solo acceso al modelo: la propia página alterna entre
          // Entrenamiento e Inferencia con sus pestañas. Quien puede entrenar
          // entra por Entrenamiento; el médico entra directo a Inferencia.
          { modulo: 'modelo', href: '/paginas/datos/modelo_ml/index.html', labelKey: 'sub_modelo_predictivo' },
          { modulo: 'prediccion', excluyeModulo: 'modelo', href: '/paginas/clinico/prediccion/index.html', labelKey: 'sub_modelo_predictivo' },
        ]},
      ],
    },
    {
      id: 'gobierno',
      labelKey: 'cat_gobierno',
      items: [
        { modulo: 'notificaciones', modulos: ['usuarios', 'notificaciones', 'auditoria', 'configuracion'], label: 'Administración del sistema', icon: 'configuracion', subs: [
          { modulo: 'notificaciones', href: '/paginas/seguridad/notificaciones/index.html', labelKey: 'sub_bandeja' },
          { modulo: 'usuarios', href: '/paginas/seguridad/usuarios/index.html', labelKey: 'sub_cuentas' },
          { modulo: 'auditoria', href: '/paginas/gobierno/auditoria/index.html', labelKey: 'sub_eventos' },
          { modulo: 'configuracion', href: '/paginas/gobierno/configuracion/index.html', labelKey: 'sub_sistema' },
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
      'laboratorio', 'urgencias', 'instrumental', 'habitaciones', 'recetas', 'farmacia', 'facturacion', 'rrhh',
      'analisis', 'prediccion', 'reportes',
      'dataset', 'pipeline', 'modelo',
      'usuarios', 'notificaciones', 'auditoria', 'configuracion',
    ],
    medico: [
      'pacientes', 'mis_citas', 'registros', 'comorbilidades',
      'laboratorio', 'urgencias', 'recetas', 'habitaciones',
      'analisis', 'prediccion', 'reportes', 'notificaciones',
    ],
    enfermero: [
      'pacientes', 'admisiones', 'citas', 'laboratorio', 'urgencias', 'instrumental', 'habitaciones',
      'comorbilidades', 'notificaciones',
    ],
    farmaceutico: [
      'pacientes', 'admisiones', 'citas', 'urgencias', 'instrumental', 'habitaciones',
      'farmacia', 'facturacion',
      'analisis', 'reportes', 'notificaciones',
    ],
    analista: [
      'analisis', 'prediccion', 'reportes',
      'facturacion', 'rrhh', 'comorbilidades',
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
    const modulos = item.modulos || [item.modulo];
    if (!modulos.some(modulo => permitidos.includes(modulo))) return false;
    const subs = this._subsVisibles(item.subs, permitidos);
    return subs.length > 0;
  },

  _moduloDesdeRuta(href) {
    const mapa = [
      ['/paginas/clinico/pacientes/', 'pacientes'],
      ['/paginas/clinico/admisiones/', 'admisiones'],
      ['/paginas/clinico/habitaciones/', 'habitaciones'],
      ['/paginas/clinico/instrumental/', 'instrumental'],
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
      if (cat.items.some(it => (it.modulos || [it.modulo]).includes(mod))) return cat.id;
    }
    return null;
  },

  _mismoPath(href, activeHref) {
    const a = String(activeHref || '').split('#')[0];
    const d = String(href || '').split('#')[0];
    return a === d || a.endsWith(d) || d.endsWith(a);
  },

  _mismoEnlace(href, activeHref) {
    if (!this._mismoPath(href, activeHref)) return false;
    const aHash = String(activeHref || '').split('#')[1] || '';
    const dHash = String(href || '').split('#')[1] || '';
    if (!dHash) return true;
    return aHash === dHash;
  },

  /** Filtra subenlaces con restricción opcional `roles: [...]` según el rol actual */
  _subsVisibles(subs, permitidos = this._permitidosRol()) {
    const rol = String((JSON.parse(localStorage.getItem('usuario') || '{}').rol || '')).toLowerCase();
    return (subs || []).filter(s =>
      (!s.roles || s.roles.includes(rol)) &&
      (!s.modulo || !permitidos || permitidos.includes(s.modulo)) &&
      // Para no duplicar una entrada cuando dos páginas son el mismo módulo:
      // quien tiene el permiso "grande" no ve además la versión reducida.
      (!s.excluyeModulo || !permitidos || !permitidos.includes(s.excluyeModulo))
    );
  },

  _itemHtml(item, activeHref) {
    const proximo = this._esProximo(item);
    const subs = this._subsVisibles(item.subs);
    if (!subs.length) return '';

    const label = this._txt(item);
    const title = String(label).replace(/"/g, '&quot;');

    if (subs.length === 1) {
      const sub = subs[0];
      const active = this._mismoEnlace(sub.href, activeHref);
      const badge = proximo ? '<span class="nav-badge">próximo</span>' : '';
      const h = String(sub.href).replace(/'/g, "\\'");
      return `<a class="nav-group-link${active ? ' active' : ''}${proximo ? ' nav-link-proximo' : ''}" href="${sub.href}" data-modulo="${item.modulo}" title="${title}"${proximo ? ' data-proximo="1"' : ''} onclick="return DiabCareNav.irModulo(event,'${h}')">
        <span class="nav-group-icon">${DiabCareIcons.nav(item.icon || item.modulo)}</span>
        <span class="nav-group-label">${label}</span>${badge}
      </a>`;
    }

    const isActiveGroup = subs.some(s => this._mismoPath(s.href, activeHref));
    const primary = subs[0].href;
    let html = `<div class="nav-group${proximo ? ' nav-group-proximo' : ''}" data-modulo="${item.modulo}"${proximo ? ' data-proximo="1"' : ''}>`;
    html += `<div class="nav-group-header${isActiveGroup ? ' open' : ''}" onclick="DiabCareNav.toggleModulo(this)" title="${title}" data-primary-href="${primary}">`;
    html += `<span class="nav-group-icon">${DiabCareIcons.nav(item.icon || item.modulo)}</span>`;
    html += `<span class="nav-group-label">${label}</span>`;
    if (proximo) html += '<span class="nav-badge">próximo</span>';
    html += `<span class="nav-chevron">${DiabCareIcons.svg('chevron', 12)}</span></div>`;
    html += `<div class="nav-sub-compact${isActiveGroup ? ' open' : ''}">`;
    for (const sub of subs) {
      const active = this._mismoEnlace(sub.href, activeHref);
      const h = String(sub.href).replace(/'/g, "\\'");
      html += `<a class="nav-sub-item${active ? ' active' : ''}" href="${sub.href}" onclick="return DiabCareNav.irModulo(event,'${h}')">`;
      html += `<span class="nav-sub-icon">${DiabCareIcons.nav(sub.modulo || item.modulo)}</span><span class="nav-sub-label">${this._txt(sub)}</span></a>`;
    }
    html += '</div></div>';
    return html;
  },


  init(activeHref) {
    const href = activeHref || ((window.location.pathname || '') + (window.location.hash || ''));
    let u = {};
    try { u = JSON.parse(localStorage.getItem('usuario') || '{}') || {}; } catch (_) { u = {}; }
    const enAuth = href.includes('/seguridad/autenticacion') || href === '/' || href === '/index.html';
    const enPerfil = href.includes('/seguridad/perfil');
    if (u.debe_cambiar_password && !enAuth && !enPerfil) {
      window.location.href = '/paginas/seguridad/perfil/index.html?forzar=1';
      return;
    }
    this._asegurarClicsPanel();
    try { document.body.classList.add('dc-uv'); } catch (_) { /* ignore */ }
    this._sincronizarAreaConRuta(href);
    this.render(href);
    this.aplicarRoles();
    this.aplicarEstadoColapsado();
    this._bindDockHover();
    // Topbar primero: así #tb-user-avatar existe cuando initUser pinta la foto
    this.montarTopbarAcciones();
    this.montarHolos();
    this.initUser();
    if (window.DiabCareI18n) DiabCareI18n.aplicarPagina();
    this.normalizarNombrePagina();
    this.aplicarLayoutModulo();
    if (typeof DiabCareAPI !== 'undefined') {
      DiabCareAPI.actualizarEstadoTopbar();
    }
  },

  normalizarNombrePagina() {
    const path = window.location.pathname || '';
    const hit = this.NOMBRES_RUTA.find(([re]) => re.test(path));
    if (!hit) return;
    const nombre = hit[1];
    document.title = `DiabCare - ${nombre}`;
    const topbar = document.querySelector('.tb-page');
    if (topbar) topbar.textContent = nombre;
    const titulo = document.querySelector('.page-title');
    if (!titulo) return;
    const partes = nombre.split(' ');
    titulo.textContent = partes.shift() || nombre;
    if (partes.length) {
      titulo.appendChild(document.createTextNode(' '));
      const destacado = document.createElement('span');
      destacado.textContent = partes.join(' ');
      titulo.appendChild(destacado);
    }
  },

  aplicarLayoutModulo() {
    const path = window.location.pathname || '';
    if (/\/paginas\/inicio\//i.test(path)) return;
    const hit = this.LAYOUT_RUTAS.find(([re]) => re.test(path));
    if (!hit) return;
    document.body.classList.add('dc-module-page', `dc-layout-${hit[1]}`);
    const content = document.querySelector('.content');
    if (content) content.classList.add('dc-module-content');
    const header = content?.querySelector(':scope > .page-header, :scope > .gen-hero, :scope > .an-hero');
    if (header) header.classList.add('dc-module-header');
    content?.querySelectorAll(':scope > .tabla-card, :scope > .panel-card, :scope > .card, :scope > .cfg-layout').forEach((el) => {
      el.classList.add('dc-module-primary');
    });
  },

  /** Ilustración clínica junto al título del módulo. */
  pintarArteModulo() {
    try {
      if (/\/paginas\/inicio\//i.test(window.location.pathname)) return;
      if (document.querySelector('.mod-clinico')) return;
      if (!window.DiabCareIcons) return;
      const title = document.querySelector('.page-title');
      if (!title) return;
      const mod = this._moduloDesdeRuta(window.location.pathname);
      if (!mod) return;
      const art = document.createElement('div');
      art.className = 'mod-clinico';
      art.setAttribute('aria-hidden', 'true');
      art.innerHTML = DiabCareIcons.ilustracion(mod);
      const header = title.closest('.page-header');
      if (header) {
        header.classList.add('page-header--clinico');
        header.insertBefore(art, header.firstChild);
        return;
      }
      const wrap = document.createElement('div');
      wrap.className = 'page-header page-header--clinico';
      title.parentNode.insertBefore(wrap, title);
      wrap.appendChild(art);
      wrap.appendChild(title);
      const sub = wrap.nextElementSibling;
      if (sub && sub.classList && sub.classList.contains('page-sub')) wrap.appendChild(sub);
    } catch (_) { /* ignore */ }
  },

  /** Markup del interruptor clínico (pulso SpO2). */
  holoHtml(opts) {
    const o = opts || {};
    const id = String(o.id || '').replace(/[^a-zA-Z0-9_-]/g, '');
    const inputId = o.inputId || (id ? `holo-${id}` : `holo-${Math.random().toString(36).slice(2, 9)}`);
    const size = o.size === 'xs' || o.size === 'sm' ? o.size : 'sm';
    const checked = o.checked ? ' checked' : '';
    const title = String(o.title || '').replace(/"/g, '&quot;');
    const off = String(o.off || 'OFF').replace(/</g, '');
    const on = String(o.on || 'ON').replace(/</g, '');
    const change = o.onchange ? ` onchange="${String(o.onchange).replace(/"/g, '&quot;')}"` : '';
    const wrapId = id ? ` id="${id}"` : '';
    return `<div class="dc-holo dc-holo--${size}"${wrapId} title="${title}">
      <div class="dc-holo-wrap">
        <input class="dc-holo-input" id="${inputId}" type="checkbox"${checked}${change} aria-label="${title}">
        <label class="dc-holo-track" for="${inputId}">
          <div class="dc-holo-lines"><div class="dc-holo-line"></div></div>
          <div class="dc-holo-thumb">
            <div class="dc-holo-core"></div>
            <div class="dc-holo-inner"></div>
            <div class="dc-holo-scan"></div>
            <div class="dc-holo-particles">
              <div class="dc-holo-particle"></div><div class="dc-holo-particle"></div>
              <div class="dc-holo-particle"></div><div class="dc-holo-particle"></div>
              <div class="dc-holo-particle"></div>
            </div>
          </div>
          <div class="dc-holo-data">
            <div class="dc-holo-txt off">${off}</div>
            <div class="dc-holo-txt on">${on}</div>
            <div class="dc-holo-dot off"></div>
            <div class="dc-holo-dot on"></div>
          </div>
          <div class="dc-holo-rings">
            <div class="dc-holo-ring"></div><div class="dc-holo-ring"></div><div class="dc-holo-ring"></div>
          </div>
          <div class="dc-holo-shine"></div>
          <div class="dc-holo-glow"></div>
        </label>
      </div>
    </div>`;
  },

  holoEstaOn(idOrEl) {
    const el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
    if (!el) return false;
    const inp = el.classList && el.classList.contains('dc-holo-input')
      ? el
      : el.querySelector && el.querySelector('.dc-holo-input');
    if (inp) return !!inp.checked;
    return !!(el.classList && el.classList.contains('on'));
  },

  holoPoner(idOrEl, on) {
    const el = typeof idOrEl === 'string' ? document.getElementById(idOrEl) : idOrEl;
    if (!el) return;
    const inp = (el.classList && el.classList.contains('dc-holo-input'))
      ? el
      : (el.querySelector && el.querySelector('.dc-holo-input'));
    if (inp) inp.checked = !!on;
    if (el.classList) el.classList.toggle('on', !!on);
  },

  /** Convierte los `.toggle` clásicos de Configuración / Perfil. */
  montarHolos(root) {
    const scope = root || document;
    scope.querySelectorAll('.toggle').forEach((el) => {
      if (!el || el.classList.contains('dc-holo')) return;
      if (el.querySelector && el.querySelector('.dc-holo-input')) return;
      const id = el.id || '';
      const checked = el.classList.contains('on');
      const size = el.classList.contains('sm') ? 'xs' : 'sm';
      const extra = el.getAttribute('data-onchange') || '';
      const html = this.holoHtml({
        id,
        checked,
        size,
        title: el.getAttribute('title') || '',
        onchange: extra,
      });
      el.insertAdjacentHTML('afterend', html);
      const next = el.nextElementSibling;
      el.remove();
      if (id && next && !next.id) next.id = id;
    });
  },

  syncTemaDesdeHolo(ev) {
    const on = !!(ev && ev.target && ev.target.checked);
    this.cambiarTemaAnimado(on ? 'claro' : 'oscuro', ev && ev.target);
  },

  accionesEscritorio() {
    const rol = this._rolActual();
    const permitidos = this.ACCESO[rol] || [];
    const pasos = this.ESCRITORIO_POR_ROL[rol] || this.ESCRITORIO_POR_ROL.administrador || [];
    return pasos.filter((p) => !permitidos.length || permitidos.includes(p.modulo));
  },

  /**
   * Escritorio: una “billetera” por área del rail.
   * Cada tarjeta apilada = un módulo clickeable.
   */
  areasEscritorio() {
    const permitidos = this._permitidosRol();
    const maxCards = 12;
    return this._areasVisibles().map((cat) => {
      const items = cat.items.filter((it) => this._itemVisibleParaRol(it, permitidos));
      const modules = [];
      for (const it of items) {
        const subs = this._subsVisibles(it.subs);
        const href = subs[0] && subs[0].href ? subs[0].href : '';
        if (!href) continue;
        modules.push({
          modulo: it.modulo,
          label: this._txt(it),
          href,
          icon: it.icon || it.modulo,
        });
      }
      const nombres = modules.map((m) => m.label);
      const preview = nombres.slice(0, 4);
      const hint = preview.length
        ? (preview.join(' - ') + (nombres.length > 4 ? '…' : ''))
        : this.t('home_area_h');
      return {
        area: cat.id,
        icon: this.ICONO_AREA[cat.id] || 'analisis',
        label: this._txt(cat),
        hint,
        href: modules[0] ? modules[0].href : '/paginas/inicio/index.html',
        count: modules.length,
        modules: modules.slice(0, maxCards),
        extras: Math.max(0, modules.length - maxCards),
      };
    });
  },

  /** Pocket / “ver todos”: abre el panel del área en el rail. */
  abrirAreaDesdeInicio(ev, catId) {
    if (ev && ev.preventDefault) ev.preventDefault();
    if (ev && ev.stopPropagation) ev.stopPropagation();
    this.abrirArea(catId);
    return false;
  },

  pintarTableroGuardia(host) {
    const root = host || document.getElementById('home-guardia');
    if (!root) return;
    const areas = this.areasEscritorio();
    const areasEl = document.getElementById('gx-areas');
    const listEl = document.getElementById('gx-mod-list');
    const titleEl = document.getElementById('gx-area-title');
    const countEl = document.getElementById('gx-area-count');
    if (!areasEl || !listEl) return;
    if (!areas.length) {
      areasEl.innerHTML = '';
      listEl.innerHTML = `<p class="dc-panel-empty">${this.t('home_sin_modulos')}</p>`;
      return;
    }
    const sel = root.getAttribute('data-area') || areas[0].area;
    const actual = areas.find((a) => a.area === sel) || areas[0];
    root.setAttribute('data-area', actual.area);
    const svg = (name, size) => {
      try { return DiabCareIcons.svg(name, size); } catch (_) { return ''; }
    };
    areasEl.innerHTML = areas.map((a) => `
      <button type="button" class="gx-area${a.area === actual.area ? ' is-on' : ''}"
        data-area="${a.area}" onclick="DiabCareNav.elegirAreaGuardia('${a.area}')">
        <span class="gx-area-ico">${svg(a.icon, 16)}</span>
        <span>
          <strong>${a.label}</strong>
          <small>${a.count} ${this.t('home_modulos')}</small>
        </span>
      </button>`).join('');
    if (titleEl) titleEl.textContent = actual.label;
    if (countEl) countEl.textContent = `${actual.count} ${this.t('home_modulos')}`;
    listEl.innerHTML = (actual.modules || []).map((m) => `
      <a class="gx-mod" href="${m.href}">
        <span class="gx-mod-ico">${svg(m.icon || m.modulo, 16)}</span>
        <span>${m.label}</span>
        <em>abrir</em>
      </a>`).join('');
  },

  elegirAreaGuardia(areaId) {
    const root = document.getElementById('home-guardia');
    if (!root) return;
    root.setAttribute('data-area', areaId);
    this.pintarTableroGuardia(root);
  },

  /** @deprecated el escritorio ya no usa flip 3D. */
  toggleHomeFlip() {
    return false;
  },

  /** @deprecated alias */
  toggleWallet(ev, el) {
    return this.toggleHomeFlip(ev, el);
  },

  _areasVisibles() {
    const permitidos = this._permitidosRol();
    return this.CATEGORIAS.filter((cat) =>
      cat.items.some((it) => this._itemVisibleParaRol(it, permitidos))
    );
  },

  _areaGuardada() {
    try { return localStorage.getItem('diabcare_area') || 'inicio'; } catch (_) { return 'inicio'; }
  },

  _setArea(area) {
    try { localStorage.setItem('diabcare_area', area || 'inicio'); } catch (_) { /* ignore */ }
  },

  /**
   * Área del rail/panel.
   * En Inicio: respeta la elección del rail.
   * En módulos: usa el área guardada (clic del rail); no la pisa con la ruta
   * (si no, Farmacia/Negocio nunca se podían abrir estando en Pacientes).
   */
  _areaActual(href) {
    const path = href || window.location.pathname || '';
    const enInicio = /\/paginas\/inicio\//i.test(path);
    const guardada = this._areaGuardada();
    if (enInicio) {
      if (guardada && guardada !== 'inicio') return guardada;
      return 'inicio';
    }
    if (guardada && guardada !== 'inicio') return guardada;
    return this._categoriaActiva(path) || 'inicio';
  },

  /** Al cargar una página de módulo, alinear el rail con esa ruta. */
  _sincronizarAreaConRuta(href) {
    const path = href || window.location.pathname || '';
    if (/\/paginas\/inicio\//i.test(path)) return;
    const porRuta = this._categoriaActiva(path);
    if (porRuta) this._setArea(porRuta);
  },

  panelAbierto() {
    try { return localStorage.getItem('diabcare_sidebar_colapsada') !== '1'; } catch (_) { return true; }
  },

  setPanelAbierto(open) {
    try { localStorage.setItem('diabcare_sidebar_colapsada', open ? '0' : '1'); } catch (_) { /* ignore */ }
  },

  irInicio(ev) {
    this._dockPinned = false;
    this._ocultarMenu({ force: true });
    this._setArea('inicio');
    this.setPanelAbierto(false);
    if (/\/paginas\/inicio\//i.test(window.location.pathname || '')) {
      if (ev && ev.preventDefault) ev.preventDefault();
      this.render(window.location.pathname);
      this.aplicarRoles();
      this.aplicarEstadoColapsado();
    }
  },

  /** Navegación dura a un módulo (evita clics tragados por overlays). */
  irModulo(ev, href) {
    if (ev) {
      try { ev.preventDefault(); } catch (_) { /* ignore */ }
      try { ev.stopPropagation(); } catch (_) { /* ignore */ }
    }
    const dest = String(href || '').trim();
    if (!dest || dest === '#' || dest.startsWith('javascript:')) return false;
    try {
      const u = new URL(dest, window.location.origin);
      if (u.pathname === window.location.pathname && u.search === (window.location.search || '')) {
        if (u.hash && u.hash !== window.location.hash) window.location.hash = u.hash;
        return false;
      }
    } catch (_) { /* seguir */ }
    if (!window.DiabCareNavigate || !window.DiabCareNavigate(dest)) window.location.assign(dest);
    return false;
  },

  colapsarPanel() {
    this._dockPinned = false;
    this.setPanelAbierto(false);
    this._ocultarMenu({ force: true });
    this._marcarRail();
  },

  abrirArea(catId) {
    const area = String(catId || 'inicio');
    if (area === 'inicio') {
      this.irInicio();
      if (!/\/paginas\/inicio\//i.test(window.location.pathname || '')) {
        if (!window.DiabCareNavigate || !window.DiabCareNavigate('/paginas/inicio/index.html')) {
          window.location.href = '/paginas/inicio/index.html';
        }
      }
      return;
    }
    const btn = document.querySelector(`.dc-rail-btn[data-area="${area}"]`);
    if (this._dockPinned && this._menuArea === area) {
      this.colapsarPanel();
      return;
    }
    this._dockPinned = true;
    this._setArea(area);
    this.setPanelAbierto(true);
    this._mostrarMenu(area, btn);
  },

  _panelItemsHtml(areaId, href, permitidos) {
    const cat = this.CATEGORIAS.find((c) => c.id === areaId);
    if (!cat) return `<p class="dc-panel-empty">${this.t('home_elige_area')}</p>`;
    const items = cat.items.filter((it) => this._itemVisibleParaRol(it, permitidos));
    if (!items.length) return `<p class="dc-panel-empty">${this.t('home_sin_modulos')}</p>`;
    return items.map((it) => this._itemHtml(it, href)).join('');
  },

  _bindDockHover() {
    if (this._dockHoverBound) return;
    this._dockHoverBound = true;
    document.addEventListener('pointerover', (ev) => {
      const shell = document.getElementById('diabcare-sidebar');
      if (!shell || !ev.target || !ev.target.closest) return;
      if (!ev.target.closest('#diabcare-sidebar')) return;
      clearTimeout(this._dockLeaveTimer);
      if (ev.target.closest('a.dc-rail-btn') && !ev.target.closest('[data-area]')) {
        if (!this._dockPinned) this._programarOcultarMenu();
        return;
      }
      const btn = ev.target.closest('.dc-rail-btn[data-area]');
      if (!btn) return;
      this._mostrarMenu(btn.getAttribute('data-area'), btn);
    });
    document.addEventListener('pointerout', (ev) => {
      const shell = document.getElementById('diabcare-sidebar');
      if (!shell) return;
      const from = ev.target;
      const to = ev.relatedTarget;
      const inside = (el) => el && el.closest && el.closest('#diabcare-sidebar');
      if (inside(from) && !inside(to)) this._programarOcultarMenu();
    });
    window.addEventListener('resize', () => {
      if (!this._menuArea) return;
      const btn = document.querySelector(`.dc-rail-btn[data-area="${this._menuArea}"]`);
      if (btn) this._alinearMenu(btn);
    });
    document.addEventListener('click', (ev) => {
      const shell = document.getElementById('diabcare-sidebar');
      if (!shell) return;
      if (ev.target && ev.target.closest && ev.target.closest('#diabcare-sidebar')) return;
      if (this._dockPinned) this.colapsarPanel();
      else this._ocultarMenu();
    });
  },

  _programarOcultarMenu() {
    clearTimeout(this._dockLeaveTimer);
    this._dockLeaveTimer = setTimeout(() => {
      if (this._dockPinned) return;
      this._ocultarMenu();
    }, 180);
  },

  _mostrarMenu(areaId, btn) {
    const area = String(areaId || '');
    if (!area || area === 'inicio') return;
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    clearTimeout(this._dockLeaveTimer);
    this._menuArea = area;
    const href = window.location.pathname;
    const permitidos = this._permitidosRol();
    const cat = this.CATEGORIAS.find((c) => c.id === area);
    const lab = cat ? this._txt(cat) : area;
    let panel = document.getElementById('dc-shell-panel');
    if (!panel) {
      mount.insertAdjacentHTML('beforeend', `<div class="dc-panel is-open" id="dc-shell-panel">
        <div class="dc-panel-head"><span class="dc-panel-title"></span></div>
        <nav class="dc-panel-nav"></nav>
      </div>`);
      panel = document.getElementById('dc-shell-panel');
    }
    const tit = panel.querySelector('.dc-panel-title');
    const nav = panel.querySelector('.dc-panel-nav');
    if (tit) tit.textContent = lab;
    if (nav) nav.innerHTML = this._panelItemsHtml(area, href, permitidos);
    panel.classList.add('is-open');
    panel.classList.toggle('is-pinned', !!this._dockPinned);
    const alineado = btn || mount.querySelector(`.dc-rail-btn[data-area="${area}"]`);
    this._alinearMenu(alineado);
    this._marcarRail(area);
    requestAnimationFrame(() => this._alinearMenu(alineado));
  },

  _ocultarMenu(opts) {
    if (this._dockPinned && !(opts && opts.force)) return;
    const panel = document.getElementById('dc-shell-panel');
    if (panel) panel.remove();
    this._menuArea = '';
    this._marcarRail('');
  },

  _alinearMenu(btn) {
    const panel = document.getElementById('dc-shell-panel');
    const shell = document.getElementById('diabcare-sidebar');
    if (!panel || !shell || !btn) return;
    const s = shell.getBoundingClientRect();
    const b = btn.getBoundingClientRect();
    let x = (b.left + b.width / 2) - s.left;
    const half = Math.min(panel.offsetWidth || 240, 300) / 2;
    x = Math.max(half + 10, Math.min(s.width - half - 10, x));
    panel.style.setProperty('--dc-panel-x', `${Math.round(x)}px`);
  },

  _marcarRail(areaAbierta) {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    const href = window.location.pathname || '';
    const enInicio = /\/paginas\/inicio\//i.test(href);
    const actual = this._categoriaActiva(href);
    const abierta = areaAbierta || this._menuArea || '';
    mount.querySelectorAll('.dc-rail-btn[data-area]').forEach((b) => {
      const id = b.getAttribute('data-area');
      b.classList.toggle('active', abierta === id);
      b.classList.toggle('is-current', !enInicio && actual === id);
    });
    const home = mount.querySelector('.dc-rail-nav > a.dc-rail-btn');
    if (home) home.classList.toggle('active', enInicio && !abierta);
  },

  render(activeHref) {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    const href = activeHref || ((window.location.pathname || '') + (window.location.hash || ''));
    const areas = this._areasVisibles();
    const enInicio = /\/paginas\/inicio\//i.test(href);
    const areaRuta = this._categoriaActiva(href);

    if (localStorage.getItem('diabcare_sidebar_colapsada') == null) {
      this.setPanelAbierto(false);
    }

    const hospital = this.t('hospital');
    const titInicio = this.t('home_inicio');
    const esc = (s) => String(s || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
    let rail = '';
    rail += `<a class="dc-rail-btn${enInicio ? ' active' : ''}" href="/paginas/inicio/index.html" aria-label="${esc(titInicio)}" onclick="DiabCareNav.irInicio(event)">${DiabCareIcons.svg('home', 18)}<span class="dc-rail-name">${esc(titInicio)}</span></a>`;
    for (const cat of areas) {
      const ico = this.ICONO_AREA[cat.id] || 'analisis';
      const lab = this._txt(cat);
      const current = !enInicio && areaRuta === cat.id;
      rail += `<button type="button" class="dc-rail-btn${current ? ' is-current' : ''}" data-area="${cat.id}" aria-label="${esc(lab)}" onclick="DiabCareNav.abrirArea('${cat.id}')">${DiabCareIcons.svg(ico, 18)}<span class="dc-rail-name">${esc(lab)}</span></button>`;
    }

    mount.classList.add('dc-shell');
    mount.innerHTML = `
      <div class="dc-rail">
        <a class="dc-rail-logo" href="/paginas/inicio/index.html" title="DiabCare" onclick="DiabCareNav.irInicio(event)">
          <img src="/estaticos/img/logo-icon.svg" alt="DiabCare" width="28" height="28">
        </a>
        <div class="dc-rail-nav">${rail}</div>
        <div class="dc-rail-foot"><span class="dc-rail-hint">${hospital}</span></div>
      </div>`;
    this._asegurarClicsPanel();
    this._bindDockHover();
    if (this._dockPinned && this._menuArea && this._menuArea !== 'inicio') {
      this._mostrarMenu(this._menuArea, mount.querySelector(`.dc-rail-btn[data-area="${this._menuArea}"]`));
    }
  },

  /**
   * Si .main queda encima del panel, el <a> no es el target.
   * No toca el rail ni el botón comprimir.
   */
  _asegurarClicsPanel() {
    if (this._dcNavDocBound) return;
    this._dcNavDocBound = true;
    document.addEventListener('click', (ev) => {
      const side = document.getElementById('diabcare-sidebar');
      if (!side) return;
      // Rail / cerrar: dejar el onclick nativo
      if (ev.target && ev.target.closest
          && ev.target.closest('.dc-rail, .dc-panel-close, .dc-panel-head')) {
        return;
      }
      const r = side.getBoundingClientRect();
      const x = ev.clientX;
      const y = ev.clientY;
      if (x < r.left || x > r.right || y < r.top || y > r.bottom) return;

      let a = null;
      if (ev.target && ev.target.closest) {
        a = ev.target.closest('#diabcare-sidebar a.nav-group-link, #diabcare-sidebar a.nav-sub-item');
      }
      if (!a && typeof document.elementsFromPoint === 'function') {
        const stack = document.elementsFromPoint(x, y) || [];
        for (const el of stack) {
          if (!el || !el.closest) continue;
          const hit = el.closest('a.nav-group-link, a.nav-sub-item');
          if (hit && side.contains(hit)) {
            a = hit;
            break;
          }
        }
      }
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href === '#' || href.startsWith('javascript:')) return;
      try {
        const dest = new URL(href, window.location.origin);
        if (dest.pathname === window.location.pathname
            && dest.search === (window.location.search || '')) return;
      } catch (_) { /* seguir */ }
      ev.preventDefault();
      ev.stopPropagation();
      if (!window.DiabCareNavigate || !window.DiabCareNavigate(href)) window.location.assign(href);
    }, true);
  },

  estaColapsada() {
    return !this.panelAbierto();
  },

  aplicarEstadoColapsado() {
    const mount = document.getElementById('diabcare-sidebar');
    if (!mount) return;
    const uv = document.body.classList.contains('dc-uv') && !document.body.classList.contains('dc-auth');
    const tienePanel = !!mount.querySelector('#dc-shell-panel');
    const soloRail = uv || !this.panelAbierto() || !tienePanel;
    mount.classList.toggle('dc-shell--rail-only', soloRail);
    mount.classList.toggle('collapsed', soloRail);
    document.body.classList.toggle('sidebar-collapsed', soloRail);
    document.body.classList.toggle('dc-shell-on', true);
    if (uv) {
      mount.style.width = '';
      mount.style.minWidth = '';
      mount.style.maxWidth = '';
    } else if (soloRail) {
      mount.style.width = '64px';
      mount.style.minWidth = '64px';
      mount.style.maxWidth = '64px';
    } else {
      mount.style.width = '284px';
      mount.style.minWidth = '284px';
      mount.style.maxWidth = 'none';
    }
    this._asegurarClicsPanel();
  },

  toggleColapso() {
    this.setPanelAbierto(!this.panelAbierto());
    // Si se abre sin área de módulo, abrir la primera visible
    if (this.panelAbierto()) {
      const area = this._areaActual(window.location.pathname);
      if (!area || area === 'inicio') {
        const first = this._areasVisibles()[0];
        if (first) {
          try { localStorage.setItem('diabcare_area', first.id); } catch (_) { /* ignore */ }
          this.render(window.location.pathname);
          this.aplicarRoles();
        }
      } else {
        this.render(window.location.pathname);
        this.aplicarRoles();
      }
    } else {
      const panel = document.getElementById('dc-shell-panel');
      if (panel) panel.remove();
    }
    this.aplicarEstadoColapsado();
  },

  _rolActual() {
    try {
      return String((JSON.parse(localStorage.getItem('usuario') || '{}').rol || '')).toLowerCase();
    } catch {
      return '';
    }
  },

  temaActual() {
    return document.documentElement.getAttribute('data-tema') === 'claro' ? 'claro' : 'oscuro';
  },

  aplicarTema(tema) {
    const t = tema === 'claro' ? 'claro' : 'oscuro';
    document.documentElement.setAttribute('data-tema', t);
    try { localStorage.setItem('diabcare_tema', t); } catch (_) { /* ignore */ }
    const title = this.t(t === 'oscuro' ? 'tb_tema_claro' : 'tb_tema_oscuro');
    document.querySelectorAll('#tb-tema, #btn-tema, #tb-tema-btn').forEach((wrap) => {
      wrap.title = title;
      wrap.setAttribute('aria-label', title);
      const inp = wrap.querySelector ? wrap.querySelector('.dc-holo-input') : null;
      if (inp) {
        inp.checked = t === 'claro';
        inp.setAttribute('aria-label', title);
      }
    });
    const btn = document.getElementById('tb-tema-btn');
    if (btn && window.DiabCareIcons) {
      const lab = t === 'claro'
        ? (this.idiomaActual() === 'en' ? 'Dark' : 'Oscuro')
        : (this.idiomaActual() === 'en' ? 'Light' : 'Claro');
      btn.innerHTML = `${DiabCareIcons.svg(t === 'claro' ? 'luna' : 'sol', 16)}<span class="tb-idioma-lab">${lab}</span>`;
    }
    window.dispatchEvent(new CustomEvent('diabcare:tema', { detail: { tema: t } }));
  },

  cambiarTemaAnimado(tema, origen) {
    const next = tema === 'claro' ? 'claro' : 'oscuro';
    const root = document.documentElement;
    if (this.temaActual() === next) return;
    if (!document.startViewTransition) {
      this.aplicarTema(next);
      return;
    }
    root.classList.add('dc-theme-changing');
    const transition = document.startViewTransition(() => this.aplicarTema(next));
    transition.finished.finally(() => root.classList.remove('dc-theme-changing'));
  },

  toggleTema(ev) {
    if (ev && ev.target && ev.target.classList && ev.target.classList.contains('dc-holo-input')) {
      this.cambiarTemaAnimado(ev.target.checked ? 'claro' : 'oscuro', ev.target);
      return;
    }
    this.cambiarTemaAnimado(this.temaActual() === 'oscuro' ? 'claro' : 'oscuro');
  },

  /** Lee un token CSS resuelto del tema activo. Para dibujar en canvas. */
  token(nombre, respaldo = '') {
    const v = getComputedStyle(document.documentElement).getPropertyValue(nombre);
    return (v || '').trim() || respaldo;
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

    // Los textos dibujados en <canvas> (ejes, leyendas) no los alcanza el DOM.
    window.dispatchEvent(new CustomEvent('diabcare:idioma', { detail: { idioma: idi } }));

    if (typeof DiabCareAPI !== 'undefined' && DiabCareAPI.toast) {
      DiabCareAPI.toast(this.t('idioma_ok'), 'success');
    }
  },

  /** Acciones fijas a la derecha del topbar (tema, idioma, notificaciones, config, perfil). */
  montarTopbarAcciones(forzar) {
    const topbar = document.querySelector('.main .topbar');
    if (!topbar) return;

    let route = Array.from(topbar.children).find((el) => el.classList.contains('tb-route'));
    if (!route) {
      const routeNodes = Array.from(topbar.children).filter((el) => (
        el.matches('.tb-crumb, .tb-sep, .tb-page')
      ));
      if (routeNodes.length) {
        route = document.createElement('div');
        route.className = 'tb-route';
        topbar.insertBefore(route, routeNodes[0]);
        routeNodes.forEach((el) => route.appendChild(el));
      }
    }

    if (!forzar && topbar.querySelector('#tb-acciones')) return;

    let right = topbar.querySelector('.tb-right');
    if (!right) {
      right = document.createElement('div');
      right.className = 'tb-right';
      topbar.appendChild(right);
    }

    // Quitar chip MinIO / acciones previas: el perfil ocupa ese lugar
    topbar.querySelectorAll('.dc-vitals-card').forEach(el => el.remove());
    right.querySelectorAll('.tb-online, #tb-acciones, .tb-user-wrap, .dc-clinic-brand').forEach(el => el.remove());

    const acciones = document.createElement('div');
    acciones.id = 'tb-acciones';
    acciones.className = 'tb-acciones';

    const tema = this.temaActual();
    const idi = this.idiomaActual();
    const clinicTitle = 'DiabCare';
    const clinicSub = idi === 'en' ? 'Metabolic care unit' : 'Unidad de atención metabólica';
    const u = JSON.parse(localStorage.getItem('usuario') || '{}');
    const rol = (u.rol || '').toLowerCase();
    const permitidos = this.ACCESO[rol] || [];
    const verNotif = !permitidos.length || permitidos.includes('notificaciones');
    const verConfig = permitidos.includes('configuracion');
    const hrefConfig = verConfig
      ? '/paginas/gobierno/configuracion/index.html#sistema'
      : '/paginas/seguridad/perfil/index.html';
    const titleConfig = this.t(verConfig ? 'tb_config' : 'tb_preferencias');
    const titleTema = this.t(tema === 'oscuro' ? 'tb_tema_claro' : 'tb_tema_oscuro');
    const letra = ((u.nombre || 'U')[0] || 'U').toUpperCase();
    const labTema = tema === 'claro'
      ? (this.idiomaActual() === 'en' ? 'Dark' : 'Oscuro')
      : (this.idiomaActual() === 'en' ? 'Light' : 'Claro');
    const icoTema = DiabCareIcons.svg(tema === 'claro' ? 'luna' : 'sol', 16);

    acciones.innerHTML = `
      <button type="button" class="tb-icon-btn" id="tb-tema-btn" title="${titleTema}" onclick="DiabCareNav.toggleTema()">
        ${icoTema}<span class="tb-idioma-lab">${labTema}</span>
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
    const vitalsCard = document.createElement('div');
    vitalsCard.className = 'dc-vitals-card';
    vitalsCard.setAttribute('aria-label', `${clinicTitle}. ${clinicSub}`);
    vitalsCard.innerHTML = `
      <span class="dc-vitals-orbit" aria-hidden="true">
        <span class="dc-vitals-ring"></span>
        <span class="dc-vitals-core">${DiabCareIcons.svg('diabetes', 19)}</span>
      </span>
      <span class="dc-vitals-copy">
        <strong>${clinicTitle}</strong>
        <small>${clinicSub}</small>
      </span>
      <span class="dc-vitals-monitor" aria-hidden="true">
        <svg viewBox="0 0 86 32" preserveAspectRatio="none">
          <path class="dc-vitals-grid" d="M0 8H86M0 16H86M0 24H86M18 0V32M36 0V32M54 0V32M72 0V32"/>
          <path class="dc-vitals-wave" d="M1 18h12l5-9 7 18 8-15 6 6h10l5-8 7 16 7-12 5 4h12"/>
        </svg>
        <span class="dc-vitals-scan"></span>
      </span>
    `;
    topbar.insertBefore(vitalsCard, right);
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
    topbar.querySelectorAll('.tb-ecg').forEach((el) => el.remove());

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

  haySesionLocal() {
    try {
      // `dc_sesion_ok` vive en sessionStorage, que es por pestaña: al abrir una
      // pestaña nueva se perdía y el panel de notificaciones se quedaba en
      // "Cargando…" para siempre, con la cookie de sesión perfectamente válida.
      // `usuario` lo escribe el login en localStorage y se borra al cerrar
      // sesión, así que sobrevive entre pestañas. La cookie sigue mandando: si
      // caducó, la llamada devuelve 401 y el propio fetch cierra la sesión.
      return sessionStorage.getItem('dc_sesion_ok') === '1'
        || localStorage.getItem('token') === 'sesion'
        || !!localStorage.getItem('usuario');
    } catch {
      return false;
    }
  },

  marcarSesion(usuario) {
    try {
      sessionStorage.setItem('dc_sesion_ok', '1');
      if (usuario) {
        const raw = JSON.stringify(usuario);
        sessionStorage.setItem('usuario', raw);
        localStorage.setItem('usuario', raw);
      }
      localStorage.removeItem('token');
    } catch (_) { /* ignore */ }
  },

  limpiarSesionCliente() {
    try {
      sessionStorage.removeItem('dc_sesion_ok');
      sessionStorage.removeItem('usuario');
      localStorage.removeItem('token');
      localStorage.removeItem('usuario');
    } catch (_) { /* ignore */ }
  },

  async cargarBadgeNotificaciones() {
    const badge = document.getElementById('tb-notif-badge');
    if (!badge || !this.haySesionLocal()) return;
    try {
      const r = await fetch(`${this.getApi()}/api/notificaciones/?limit=1&solo_no_leidas=true`, {
        credentials: 'include',
        cache: 'no-store',
        silent: true,
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
    if (!lista || !this.haySesionLocal()) return;
    lista.innerHTML = `<div class="tb-notif-loading">${this.t('cargando')}</div>`;
    try {
      const r = await fetch(`${this.getApi()}/api/notificaciones/?limit=8&solo_no_leidas=false`, {
        credentials: 'include',
        cache: 'no-store',
        silent: true,
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
          <div class="n-meta">${para ? `${this.t('tb_notif_para')}: ${para} - ` : ''}${fecha}</div>
        </button>`;
      }).join('');
    } catch (_) {
      lista.innerHTML = `<div class="tb-notif-empty">${this.t('tb_notif_error')}</div>`;
    }
  },

  async abrirNotif(id, yaLeida) {
    if (this.haySesionLocal() && id && !yaLeida) {
      try {
        await fetch(`${this.getApi()}/api/notificaciones/${id}/leida`, {
          method: 'PATCH',
          credentials: 'include',
        });
      } catch (_) { /* ignore */ }
    }
    window.location.href = '/paginas/seguridad/notificaciones/index.html';
  },

  async marcarTodasNotif(ev) {
    if (ev) ev.stopPropagation();
    if (!this.haySesionLocal()) return;
    try {
      await fetch(`${this.getApi()}/api/notificaciones/leer-todas`, {
        method: 'POST',
        credentials: 'include',
      });
      await this.cargarPanelNotificaciones();
      this.cargarBadgeNotificaciones();
    } catch (_) { /* ignore */ }
  },

  /** Carga foto de perfil en un contenedor circular (topbar / sidebar). */
  _aplicarFotoAvatar(av, nombre, bust) {
    if (!av) return;
    const letra = ((nombre || 'U')[0] || 'U').toUpperCase();
    // Ruta relativa: misma origen + cookie httpOnly (evita localhost vs 127.0.0.1)
    const url = `/api/auth/perfil/foto?t=${encodeURIComponent(bust || Date.now())}`;
    av.innerHTML = '';
    av.textContent = letra;
    const img = document.createElement('img');
    img.alt = nombre || 'Usuario';
    img.src = url;
    img.decoding = 'async';
    img.loading = 'eager';
    img.onload = () => {
      if (!av.isConnected) return;
      av.innerHTML = '';
      av.appendChild(img);
    };
    img.onerror = () => {
      if (!av.isConnected) return;
      av.textContent = letra;
    };
  },

  pintarAvatarTopbar(u) {
    const av = document.getElementById('tb-user-avatar');
    if (!av) return;
    const nombre = (u && u.nombre) || 'U';
    const nameEl = document.getElementById('tb-user-name');
    const rolEl = document.getElementById('tb-user-rol');
    if (nameEl) nameEl.textContent = (u && u.nombre) || nombre;
    if (rolEl) rolEl.textContent = this.etiquetaRol(u && u.rol);
    // Intentar siempre: la cookie basta; no depender de haySesionLocal
    this._aplicarFotoAvatar(av, nombre, (u && u.foto_bust) || Date.now());
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

  async initUser() {
    let u = {};
    try {
      u = JSON.parse(localStorage.getItem('usuario') || sessionStorage.getItem('usuario') || '{}');
    } catch (_) { u = {}; }

    // Validar cookie httpOnly en servidor
    try {
      const r = await fetch(`${this.getApi()}/api/auth/sesion`, {
        credentials: 'include',
        cache: 'no-store',
      });
      const d = await r.json();
      if (!d.ok || !d.autenticado) {
        this.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
        return;
      }
      u = { ...u, ...(d.usuario || {}) };
      this.marcarSesion(u);
    } catch (_) {
      if (!this.haySesionLocal() && !(u && u.email)) {
        this.forzarCierreSesion();
        return;
      }
    }

    // Completar tiene_foto desde perfil si hace falta
    if (u.tiene_foto == null) {
      try {
        const rp = await fetch(`${this.getApi()}/api/auth/perfil`, {
          credentials: 'include',
          cache: 'no-store',
        });
        if (rp.ok) {
          const pu = await rp.json();
          if (pu && !pu.detail) {
            u = { ...u, ...pu };
            this.marcarSesion(u);
          }
        }
      } catch (_) { /* ignore */ }
    }

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
    this._aplicarFotoAvatar(av, nombre, (u && u.foto_bust) || Date.now());
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
    const rol = String(u.rol || '').toLowerCase();
    const permitidos = this.ACCESO[rol];
    if (!permitidos) return;

    document.querySelectorAll('[data-modulo]').forEach(el => {
      const mod = el.dataset.modulo;
      el.style.display = permitidos.includes(mod) ? '' : 'none';
    });

    document.querySelectorAll('.nav-cat-block[data-categoria], .dc-panel-sec[data-categoria]').forEach(block => {
      const items = block.querySelectorAll('[data-modulo]');
      const visibles = [...items].some(el => el.style.display !== 'none');
      block.style.display = visibles ? '' : 'none';
    });
  },

  async cerrarSesion() {
    try {
      const ctrl = new AbortController();
      const to = setTimeout(() => ctrl.abort(), 2500);
      try {
        await fetch(`${this.getApi()}/api/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          signal: ctrl.signal,
        });
      } finally {
        clearTimeout(to);
      }
    } catch (_) { /* ignore: sesión ya inválida o red */ }
    sessionStorage.setItem('logout', '1');
    this.limpiarSesionCliente();
    const temaKeep = localStorage.getItem('diabcare_tema');
    const idiKeep = localStorage.getItem('diabcare_idioma');
    localStorage.clear();
    if (temaKeep) localStorage.setItem('diabcare_tema', temaKeep);
    if (idiKeep) localStorage.setItem('diabcare_idioma', idiKeep);
    window.location.replace('/');
  },

  /** Con cookie-sesión el cliente no decodifica JWT; solo marca local. */
  tokenExpirado(token) {
    const t = token || localStorage.getItem('token');
    if (!t) return true;
    if (t === 'sesion') return false;
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
    this.limpiarSesionCliente();
    const temaKeep = localStorage.getItem('diabcare_tema');
    const idiKeep = localStorage.getItem('diabcare_idioma');
    localStorage.clear();
    if (temaKeep) localStorage.setItem('diabcare_tema', temaKeep);
    if (idiKeep) localStorage.setItem('diabcare_idioma', idiKeep);
    window.location.replace('/');
  },

  irLogin() {
    this.forzarCierreSesion();
  },

  /** Envía cookies + limpia Authorization basura; intercepta 401 + pantalla de carga. */
  instalarInterceptorAuth() {
    if (this._fetchPatched || typeof window === 'undefined') return;
    this._fetchPatched = true;
    const orig = window.fetch.bind(window);
    const self = this;

    function urlDe(input) {
      try {
        return typeof input === 'string' ? input : (input && input.url) || '';
      } catch (_) {
        return '';
      }
    }

    window.fetch = async function diabcareFetch(input, init) {
      const opts = init ? { ...init } : {};
      if (opts.credentials == null) opts.credentials = 'include';
      try {
        const headers = new Headers(opts.headers || (input && input.headers) || undefined);
        const auth = headers.get('Authorization') || '';
        if (/^Bearer\s*(sesion|cookie|null|undefined)?$/i.test(auth.trim()) || auth === 'Bearer ') {
          headers.delete('Authorization');
          opts.headers = headers;
        }
      } catch (_) { /* ignore */ }

      const url = urlDe(input);
      const sk = window.DiabCareSkeleton;
      const useSk = sk && sk.debeSkeletonFetch(url, opts);
      let skAt = 0;
      if (useSk) {
        skAt = sk.beginFetchSkeleton ? sk.beginFetchSkeleton() : (sk.paintAllForFetch(), Date.now());
      }
      try {
        const res = await orig(input, opts);
        if (res.status === 401) {
          if (/\/api\/auth\/(login|logout|recuperar|resetear|solicitud|registro|sesion)/i.test(url)) {
            return res;
          }
          if (self.haySesionLocal()) {
            self.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
          }
        }
        return res;
      } finally {
        if (useSk && skAt) {
          if (sk.endFetchSkeleton) await sk.endFetchSkeleton(skAt, sk.MIN_MS || 650);
          else {
            const wait = Math.max(0, (sk.MIN_MS || 650) - (Date.now() - skAt));
            if (wait) await new Promise((r) => setTimeout(r, wait));
            try { if (sk.clearExtras) sk.clearExtras(); } catch (_) { /* ignore */ }
          }
        }
      }
    };
  },

  /** Vigila la sesión preguntando al servidor (cookie), no leyendo JWT. */
  iniciarVigilanciaSesion() {
    if (this._vigilanciaOn) return;
    this._vigilanciaOn = true;
    const tick = async () => {
      if (!this.haySesionLocal()) return;
      try {
        const r = await fetch(`${this.getApi()}/api/auth/sesion`, {
          credentials: 'include',
          cache: 'no-store',
        });
        const d = await r.json();
        if (!d.ok || !d.autenticado) {
          this.forzarCierreSesion('Tu sesión finalizó. Vuelve a iniciar sesión.');
        } else if (d.usuario) {
          this.marcarSesion(d.usuario);
        }
      } catch (_) { /* red temporal: no expulsar */ }
    };
    setTimeout(tick, 8000);
    setInterval(tick, 60000);
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
    if (!this.haySesionLocal()) return;
    history.pushState({ diabcareApp: 1 }, '', location.href);
    window.addEventListener('popstate', () => {
      if (!this.haySesionLocal()) return;
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
