/**
 * DiabCare - checklist de módulos operativos.
 */
window.DiabCareRuta = {
  PASOS: [
    { id: 'login', label: 'Sesión activa',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/clinico/analisis/diabetes/index.html', check: (s) => !!s.token },
    { id: 'usuarios', label: 'Usuarios',
      roles: ['administrador'],
      href: '/paginas/seguridad/usuarios/index.html', check: (s) => s.usuarios?.total > 0 },
    { id: 'registros', label: 'Pacientes',
      roles: ['administrador', 'medico'],
      href: '/paginas/clinico/pacientes/index.html',
      check: (s) => (s.pacientes?.activos || 0) > 0 || (s.stats?.total || 0) > 0 },
    { id: 'admisiones', label: 'Admisiones',
      roles: ['administrador'],
      href: '/paginas/clinico/admisiones/index.html',
      check: (s) => (s.admisiones?.total || 0) > 0 },
    { id: 'agenda', label: 'Agenda',
      roles: ['administrador'],
      href: '/paginas/clinico/agenda/index.html',
      check: (s) => (s.citas?.total || 0) > 0 },
    { id: 'filtros', label: 'Registros clínicos',
      roles: ['administrador', 'medico'],
      href: '/paginas/clinico/registros_clinicos/index.html', check: (s) => (s.stats?.total || 0) > 0 },
    { id: 'dataset', label: 'Dataset stage',
      roles: ['administrador', 'analista'],
      href: '/paginas/datos/dataset/generador.html', check: (s) => (s.dwh?.total_stage || 0) > 0 },
    { id: 'pipeline', label: 'Pipeline ELT',
      roles: ['administrador', 'analista'],
      href: '/paginas/datos/pipeline_elt/index.html', check: (s) => s.dwh?.materializado === true },
    { id: 'calidad', label: 'Calidad diabetes',
      roles: ['administrador', 'analista'],
      href: '/paginas/clinico/analisis/diabetes/index.html', check: (s) => (s.stats?.con_diabetes || 0) > 0 },
    { id: 'stats', label: 'Estadísticas',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/clinico/analisis/estadisticas/index.html', check: (s) => (s.stats?.total || 0) > 0 },
    { id: 'prediccion', label: 'Predicción',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/clinico/prediccion/index.html', check: (s) => localStorage.getItem('diabcare_prediccion_ok') === '1' },
    { id: 'modelo', label: 'Modelo ML',
      roles: ['administrador', 'analista'],
      href: '/paginas/datos/modelo_ml/index.html', check: (s) => s.modelo === true },
    { id: 'dashboard', label: 'Dashboard',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/clinico/analisis/index.html', check: (s) => (s.stats?.total || 0) > 0 },
    { id: 'hubspot', label: 'HubSpot', pronto: true,
      roles: ['administrador'],
      href: '/paginas/integraciones/index.html', check: (s) => (s.integraciones?.hubspot?.leads_registrados || 0) > 0 },
    { id: 'stripe', label: 'Stripe', pronto: true,
      roles: ['administrador'],
      href: '/paginas/integraciones/index.html', check: (s) => (s.integraciones?.stripe?.pagos_completados || 0) > 0 },
    { id: 'api', label: 'API partner', pronto: true,
      roles: ['administrador'],
      href: '/paginas/integraciones/index.html', check: (s) => s.integraciones?.api_publica?.api_key_configurada === true },
    { id: 'openapi', label: 'API docs',
      roles: ['administrador'],
      href: '/docs', check: () => true },
    { id: 'cicd', label: 'CI/CD', pronto: true,
      roles: ['administrador'],
      href: '/paginas/integraciones/index.html', check: (s) => !!s.integraciones?.cicd?.ultimo_despliegue },
    { id: 'alertas', label: 'Notificaciones',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/seguridad/notificaciones/index.html', check: (s) => (s.notif?.total || 0) > 0 },
    { id: 'reporte', label: 'Reportes PDF',
      roles: ['administrador', 'medico', 'analista'],
      href: '/paginas/clinico/reportes/index.html', check: (s) => (s.reportes?.total || 0) > 0 },
    { id: 'auditoria', label: 'Auditoría',
      roles: ['administrador'],
      href: '/paginas/gobierno/auditoria/index.html', check: (s) => (s.auditoria?.total || 0) > 0 },
    { id: 'benchmark', label: 'Benchmarking', pronto: true,
      roles: ['administrador', 'analista'],
      href: '/paginas/benchmarking/index.html', check: (s) => s.benchmark === true },
  ],

  async _fetchJson(url, token, ms = 8000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), ms);
    try {
      const r = await fetch(url, {
        headers: { Authorization: 'Bearer ' + token },
        signal: ctrl.signal,
      });
      if (!r.ok) return null;
      return r.json();
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  },

  async recolectarEstado(api, token) {
    const estado = {
      token: !!token, dwh: {}, stats: {}, pipeline: {}, modelo: false,
      notif: {}, reportes: {}, auditoria: {}, usuarios: {},
      integraciones: {}, benchmark: false, pacientes: {}, citas: {}, admisiones: {},
    };
    const safe = (url) => this._fetchJson(url, token);
    const [stats, pipeline, modeloInfo, notifs, reportes, aud, users, pacs, citas, adm] = await Promise.all([
      safe(`${api}/api/registros/estadisticas`),
      safe(`${api}/api/pipeline/estado`),
      safe(`${api}/api/modelo-ml/info`),
      safe(`${api}/api/notificaciones/?limit=1`),
      safe(`${api}/api/reportes/`),
      safe(`${api}/api/auditoria/?limit=1`),
      safe(`${api}/api/usuarios/?limit=1`),
      safe(`${api}/api/pacientes/resumen`),
      safe(`${api}/api/citas/?limit=1`),
      safe(`${api}/api/admisiones/resumen`),
    ]);
    if (stats) estado.stats = stats;
    if (pipeline) estado.pipeline = pipeline;
    estado.dwh = {
      total_stage: pipeline?.total_archivos || stats?.total || 0,
      materializado: (pipeline?.total_elt || 0) > 0 && (stats?.total || 0) > 0,
    };
    if (modeloInfo?.disponible) estado.modelo = true;
    if (notifs?.total != null) estado.notif = { total: notifs.total };
    else if (Array.isArray(notifs?.notificaciones)) estado.notif = { total: notifs.notificaciones.length };
    if (reportes?.reportes) estado.reportes = { total: reportes.reportes.length };
    else if (Array.isArray(reportes)) estado.reportes = { total: reportes.length };
    if (aud?.total != null) estado.auditoria = { total: aud.total };
    else if (Array.isArray(aud)) estado.auditoria = { total: aud.length };
    if (Array.isArray(users)) estado.usuarios = { total: users.length };
    else if (users?.usuarios) estado.usuarios = { total: users.usuarios.length };
    else if (users?.total != null) estado.usuarios = { total: users.total };
    if (pacs) estado.pacientes = pacs;
    if (citas?.total != null) estado.citas = citas;
    if (adm) estado.admisiones = adm;
    return estado;
  },

  async render(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const api = DiabCareNav.getApi();
    const token = localStorage.getItem('token');
    let rol = '';
    try {
      rol = JSON.parse(localStorage.getItem('usuario') || '{}').rol || '';
    } catch {
      rol = '';
    }
    el.innerHTML = '<div class="loading"><div class="spinner"></div>Cargando checklist…</div>';
    try {
      const estado = await this.recolectarEstado(api, token);
      const pasos = this.PASOS.filter(p => p.roles.includes(rol));
      const pasosActivos = pasos.filter(p => !p.pronto);
      let done = 0;
      let html = '<div class="ruta-list">';
      pasos.forEach(p => {
        if (p.pronto) {
          html += `<span class="ruta-item ruta-pronto">
            <span class="ruta-badge">◇</span>
            <span class="ruta-label">${p.label}</span>
            <span class="ruta-tag-pronto">próximo</span>
          </span>`;
          return;
        }
        const ok = !!p.check(estado);
        if (ok) done++;
        html += `<a class="ruta-item${ok ? ' done' : ''}" href="${p.href}">
          <span class="ruta-badge">${ok ? '✓' : '○'}</span>
          <span class="ruta-label">${p.label}</span>
        </a>`;
      });
      html += '</div>';
      html += `<div class="ruta-footer">${done}/${pasosActivos.length} módulos listos</div>`;
      el.innerHTML = html;
    } catch (e) {
      console.error('Checklist operativo:', e);
      el.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:8px 0">No se pudo cargar el checklist. <button type="button" class="btn btn-ghost btn-sm" onclick="DiabCareRuta.render(\'ruta-operativa-panel\')">Reintentar</button></div>';
    }
  },
};
