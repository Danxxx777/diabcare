/**
 * DiabCare — cliente HTTP compartido.
 * Requiere navegacion.js cargado antes.
 */
window.DiabCareAPI = {
  get base() {
    return DiabCareNav.getApi();
  },

  token() {
    return localStorage.getItem('token') || '';
  },

  usuario() {
    try {
      return JSON.parse(localStorage.getItem('usuario') || '{}');
    } catch {
      return {};
    }
  },

  headers(extra = {}) {
    const h = { ...extra };
    const t = this.token();
    if (t) h.Authorization = `Bearer ${t}`;
    return h;
  },

  async fetch(path, opts = {}) {
    const url = path.startsWith('http') ? path : `${this.base}${path}`;
    const headers = this.headers(opts.headers || {});
    let body = opts.body;
    if (body != null && typeof body === 'object' && !(body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
      body = JSON.stringify(body);
    }
    const r = await fetch(url, { ...opts, headers, body });
    if (r.status === 401) {
      localStorage.clear();
      window.location.href = '/';
    }
    return r;
  },

  async json(path, opts = {}) {
    const r = await this.fetch(path, opts);
    let data = {};
    try {
      data = await r.json();
    } catch (_) { /* vacío */ }
    return { ok: r.ok, status: r.status, data };
  },

  toast(msg, type = 'success') {
    let el = document.getElementById('toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast';
      el.className = 'toast';
      el.innerHTML = '<span id="t-icon">✓</span><span id="t-msg"></span>';
      document.body.appendChild(el);
    }
    const icon = document.getElementById('t-icon');
    const msgEl = document.getElementById('t-msg');
    if (icon) icon.textContent = type === 'error' ? '✕' : '✓';
    if (msgEl) msgEl.textContent = msg;
    el.className = `toast show ${type}`;
    clearTimeout(el._toastTimer);
    el._toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
  },

  async health() {
    try {
      const { ok, data } = await this.json('/api/health');
      return ok ? data : null;
    } catch {
      return null;
    }
  },

  async actualizarEstadoTopbar() {
    const dot = document.querySelector('.tb-online-dot');
    const label = document.querySelector('.tb-online-label');
    if (!dot || !label) return;
    const h = await this.health();
    if (!h) {
      dot.style.background = 'var(--red)';
      label.textContent = 'Backend sin respuesta';
      label.style.color = 'var(--red)';
      return;
    }
    const minioOk = h.minio === 'conectado';
    dot.style.background = minioOk ? 'var(--green)' : 'var(--amber)';
    label.textContent = minioOk ? 'MinIO conectado' : 'MinIO degradado';
    label.style.color = minioOk ? 'var(--green)' : 'var(--amber)';
  },

  /** Diálogo de confirmación acorde al tema (sustituye window.confirm). */
  confirm(opts = {}) {
    const {
      title = 'Confirmar acción',
      message = '¿Desea continuar?',
      confirmLabel = 'Confirmar',
      cancelLabel = 'Cancelar',
      danger = false,
    } = opts;

    return new Promise((resolve) => {
      let overlay = document.getElementById('dc-confirm-overlay');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'dc-confirm-overlay';
        overlay.className = 'overlay';
        overlay.innerHTML = `
          <div class="modal" id="dc-confirm-modal" role="dialog" aria-modal="true">
            <div class="modal-icon-row">
              <div class="modal-icon" id="dc-confirm-icon">!</div>
              <div class="modal-body">
                <div class="modal-title" id="dc-confirm-title" style="margin-bottom:8px"></div>
                <div class="modal-desc" id="dc-confirm-msg"></div>
              </div>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-cancel" id="dc-confirm-cancel"></button>
              <button type="button" class="btn" id="dc-confirm-ok"></button>
            </div>
          </div>`;
        document.body.appendChild(overlay);
      }

      const modal = document.getElementById('dc-confirm-modal');
      const icon = document.getElementById('dc-confirm-icon');
      const btnOk = document.getElementById('dc-confirm-ok');
      const btnCancel = document.getElementById('dc-confirm-cancel');

      document.getElementById('dc-confirm-title').textContent = title;
      document.getElementById('dc-confirm-msg').innerHTML = message;
      btnCancel.textContent = cancelLabel;
      btnOk.textContent = confirmLabel;
      btnOk.className = danger ? 'btn btn-danger' : 'btn btn-primary';
      modal.classList.toggle('danger', danger);
      icon.className = 'modal-icon ' + (danger ? 'danger' : 'info');
      icon.textContent = danger ? '⚠' : '?';

      const close = (result) => {
        overlay.classList.remove('show');
        btnOk.onclick = null;
        btnCancel.onclick = null;
        document.removeEventListener('keydown', onKey);
        resolve(result);
      };
      const onKey = (e) => {
        if (e.key === 'Escape') close(false);
        if (e.key === 'Enter') close(true);
      };

      btnOk.onclick = () => close(true);
      btnCancel.onclick = () => close(false);
      document.addEventListener('keydown', onKey);
      overlay.classList.add('show');
      btnOk.focus();
    });
  },
};

window.authHdr = () => DiabCareAPI.headers();
