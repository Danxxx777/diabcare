/** Página placeholder para módulos hospitalarios en desarrollo. */
window.DiabCarePlaceholder = {
  init(cfg) {
    DiabCareNav.init(window.location.pathname);
    const titulo = cfg.titulo || 'Módulo';
    const desc = cfg.descripcion || 'Este módulo forma parte del HIS hospitalario DiabCare.';
    const fase = cfg.fase || 'Fase 2 - en desarrollo';
    document.title = `DiabCare - ${titulo}`;
    const crumb = document.getElementById('ph-crumb');
    if (crumb) crumb.textContent = titulo;
    const t = document.getElementById('ph-title');
    if (t) t.innerHTML = titulo;
    const d = document.getElementById('ph-desc');
    if (d) d.textContent = desc;
    const f = document.getElementById('ph-fase');
    if (f) f.textContent = fase;
    const list = document.getElementById('ph-funcs');
    if (list && cfg.funcionalidades) {
      list.innerHTML = cfg.funcionalidades.map(x => `<li>${x}</li>`).join('');
    }
  },
};
