/**
 * DiabCare - cliente HTTP compartido.
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
      if (typeof DiabCareNav !== 'undefined' && DiabCareNav.forzarCierreSesion) {
        DiabCareNav.forzarCierreSesion('Tu sesión expiró. Inicia sesión de nuevo.');
      } else {
        localStorage.clear();
        window.location.href = '/';
      }
      return r;
    }
    if (r.status === 403) {
      try {
        const clone = r.clone();
        const d = await clone.json();
        const detail = String(d.detail || '');
        if (detail.includes('contraseña temporal') || detail.includes('debe actualizar')) {
          const u = this.usuario();
          u.debe_cambiar_password = true;
          localStorage.setItem('usuario', JSON.stringify(u));
          if (!window.location.pathname.includes('/seguridad/perfil')) {
            window.location.href = '/paginas/seguridad/perfil/index.html?forzar=1';
          }
        }
      } catch (_) { /* ignore */ }
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

  /** Capitaliza una sola palabra o snake_case (estados, tipos). */
  capLabel(v) {
    const t = String(v == null ? '' : v).trim();
    if (!t || t === '-' || t === '—') return t || '—';
    if (t.includes(' ') || t.includes('·') || t.includes('/')) return t;
    if (t.includes('_')) {
      return t.split('_').filter(Boolean).map(w =>
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
      ).join(' ');
    }
    if (/^[a-záéíóúüñ]+$/i.test(t)) {
      return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
    }
    return t;
  },

  moneyFmt(v, decimals = 2) {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(decimals) : '—';
  },

  /** Tamaño de página por defecto para cuadrículas (fotos + tarjetas). */
  GRID_PAGE_SIZE: 12,

  /**
   * Contenedor del pager debajo de `.tabla-wrap` (o tras `#tablaBody`).
   */
  ensurePagerHost({ id = 'dataPager' } = {}) {
    let el = document.getElementById(id);
    if (el) return el;
    el = document.createElement('div');
    el.id = id;
    el.className = 'data-pager';
    const wrap = document.querySelector('.tabla-card .tabla-wrap')
      || document.getElementById('tablaBody')?.closest('.tabla-wrap')
      || document.getElementById('tablaBody')?.parentElement;
    if (wrap && wrap.parentNode) wrap.parentNode.insertBefore(el, wrap.nextSibling);
    else document.body.appendChild(el);
    return el;
  },

  /**
   * Paginación Anterior / Siguiente.
   * onPage(nuevaPagina) se llama al navegar.
   */
  renderPager(host, { page = 1, pageSize, total = 0, onPage } = {}) {
    if (!host) return { page: 1, pages: 1 };
    const ps = Math.max(1, Number(pageSize) || this.GRID_PAGE_SIZE);
    const tot = Math.max(0, Number(total) || 0);
    const pages = Math.max(1, Math.ceil(tot / ps) || 1);
    const p = Math.min(Math.max(1, Number(page) || 1), pages);
    if (!tot) {
      host.innerHTML = '';
      host.hidden = true;
      return { page: p, pages };
    }
    host.hidden = false;
    const from = (p - 1) * ps + 1;
    const to = Math.min(p * ps, tot);
    host.innerHTML = `
      <button type="button" class="btn btn-ghost btn-sm" data-pag="prev" ${p <= 1 ? 'disabled' : ''}>← Anterior</button>
      <span class="data-pager-info">${from}–${to} de ${tot} · Pág ${p} / ${pages}</span>
      <button type="button" class="btn btn-ghost btn-sm" data-pag="next" ${p >= pages ? 'disabled' : ''}>Siguiente →</button>
    `;
    if (typeof onPage === 'function') {
      const prev = host.querySelector('[data-pag="prev"]');
      const next = host.querySelector('[data-pag="next"]');
      if (prev) prev.onclick = () => { if (p > 1) onPage(p - 1); };
      if (next) next.onclick = () => { if (p < pages) onPage(p + 1); };
    }
    return { page: p, pages };
  },

  /**
   * Arma URL de listado con limit/offset (sustituye si ya venían en la query).
   * basePath: '/api/citas/' o '/api/citas/?fecha=2026-01-01'
   */
  listUrlWithPage(basePath, { page = 1, pageSize, q, offsetParam = 'offset', extra = {} } = {}) {
    const ps = Math.max(1, Number(pageSize) || this.GRID_PAGE_SIZE);
    const p = Math.max(1, Number(page) || 1);
    const raw = String(basePath || '');
    const qi = raw.indexOf('?');
    const path = qi >= 0 ? raw.slice(0, qi) : raw;
    const params = new URLSearchParams(qi >= 0 ? raw.slice(qi + 1) : '');
    params.delete('limit');
    params.delete('offset');
    params.delete('skip');
    params.set('limit', String(ps));
    params.set(offsetParam === 'skip' ? 'skip' : 'offset', String((p - 1) * ps));
    if (q != null && String(q).trim()) params.set('q', String(q).trim());
    else params.delete('q');
    Object.entries(extra || {}).forEach(([k, v]) => {
      if (v == null || v === '') params.delete(k);
      else params.set(k, String(v));
    });
    params.set('_', String(Date.now()));
    return `${path}?${params.toString()}`;
  },

  /**
   * Cuadrícula visual de registros (reemplazo de tablas).
   * columns: [{ key, label, render?(row), title?, badge? }]
   * actionsHtml(row) -> string HTML de botones
   * showAvatar: false para ocultar foto/iniciales del paciente
   */
  buildDataGrid({ rows, columns, idField, actionsHtml, showAvatar = true }) {
    const cols = (columns || []).filter(c => c && !c.internal);
    if (!rows || !rows.length) return '';
    const preferTitle = [
      'paciente_nombre', 'paciente', 'nombre_completo', 'nombre', 'compra_label', 'factura_label',
      'descripcion', 'concepto', 'medico', 'codigo', 'label', 'titulo',
    ];
    let titleCol = cols.find(c => c.title) || cols.find(c => preferTitle.includes(c.key));
    if (!titleCol) titleCol = cols[0];
    const badgeCol = cols.find(c => c.badge) || cols.find(c => c.key === 'estado' || c.key === 'pago_label');
    const metaCols = cols.filter(c => c !== titleCol && c !== badgeCol);

    const cell = (row, col) => {
      if (!col) return '—';
      if (typeof col.render === 'function') return col.render(row);
      const v = row[col.key];
      if (v == null || v === '') return '—';
      if (col.key === 'estado' && row.estado_label) return row.estado_label;
      return this.capLabel ? (typeof v === 'string' && !String(v).includes(' ') ? this.capLabel(v) : v) : v;
    };

    const stripHtml = (html) => String(html || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    const initials = (name) => {
      const parts = stripHtml(name).split(/\s+/).filter(Boolean);
      if (!parts.length) return '?';
      const a = parts[0][0] || '';
      const b = (parts.length > 1 ? parts[parts.length - 1][0] : (parts[0][1] || '')) || '';
      return (a + b).toUpperCase();
    };
    const patientId = (row) => {
      const pid = row.id_paciente || row.paciente_id || '';
      if (pid) return String(pid);
      if (idField === 'id_paciente' && row[idField]) return String(row[idField]);
      return '';
    };
    const avatarHtml = (row, titleText) => {
      if (!showAvatar) return '';
      const pid = patientId(row);
      // Solo filas ligadas a paciente (evita avatares en listados sin id_paciente)
      if (!pid) return '';
      const name = row.paciente_nombre || row.nombre_completo || row.nombre || titleText || '';
      const ini = initials(name).replace(/[<>&"']/g, '');
      if (row.tiene_foto) {
        const api = (typeof DiabCareNav !== 'undefined' && DiabCareNav.getApi)
          ? DiabCareNav.getApi()
          : (this.baseUrl || '');
        const tok = encodeURIComponent(localStorage.getItem('token') || '');
        const src = `${api}/api/pacientes/${encodeURIComponent(pid)}/foto?token=${tok}`;
        return `<div class="data-tile-avatar" data-ini="${ini}" aria-hidden="true">
          <img src="${src}" alt="" loading="lazy"
            onerror="var p=this.parentElement;this.remove();p.classList.add('is-fallback');p.textContent=p.getAttribute('data-ini')||'?';">
        </div>`;
      }
      return `<div class="data-tile-avatar is-fallback" aria-hidden="true">${ini || '?'}</div>`;
    };

    return `<div class="data-grid">${rows.map(row => {
      const id = idField ? row[idField] : '';
      const title = cell(row, titleCol);
      const badge = badgeCol ? cell(row, badgeCol) : '';
      const meta = metaCols.map(c =>
        `<div><dt>${c.label || c.key}</dt><dd>${cell(row, c)}</dd></div>`
      ).join('');
      const acts = typeof actionsHtml === 'function' ? (actionsHtml(row, id) || '') : '';
      const av = avatarHtml(row, title);
      return `<article class="data-tile" data-id="${String(id).replace(/"/g, '&quot;')}">
        <div class="data-tile-head">
          ${av}
          <div class="data-tile-head-text">
            <h3 class="data-tile-title">${title || '—'}</h3>
            ${badge && badge !== '—' ? `<span class="data-tile-badge">${badge}</span>` : ''}
          </div>
        </div>
        ${meta ? `<dl class="data-tile-meta">${meta}</dl>` : ''}
        ${acts ? `<div class="data-tile-actions">${acts}</div>` : ''}
      </article>`;
    }).join('')}</div>`;
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
    const now = Date.now();
    if (this._healthCache && (now - this._healthAt) < 45000) {
      const h = this._healthCache;
      const minioOk = h.minio === 'conectado';
      dot.style.background = minioOk ? 'var(--green)' : 'var(--amber)';
      label.textContent = minioOk ? 'MinIO conectado' : 'MinIO degradado';
      label.style.color = minioOk ? 'var(--green)' : 'var(--amber)';
      label.style.textTransform = 'none';
      return;
    }
    const h = await this.health();
    this._healthCache = h;
    this._healthAt = now;
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
    label.style.textTransform = 'none';
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

  /**
   * Búsqueda en vivo: ranking por similitud + debounce.
   * scoreText(haystack, needle) y bindLiveSearch({ input, onSearch, delay }).
   */
  scoreText(texto, q) {
    const s = String(texto || '').toLowerCase();
    const ql = String(q || '').trim().toLowerCase();
    if (!ql || !s) return 0;
    let score = 0;
    if (s.startsWith(ql)) score += 100;
    if (s.includes(ql)) score += 50;
    ql.replace(/,/g, ' ').split(/\s+/).filter(t => t.length >= 2).forEach(tok => {
      if (s.includes(tok)) score += 15;
    });
    return score;
  },

  rankRows(rows, q, getText) {
    const ql = String(q || '').trim();
    if (!ql) return rows.slice();
    return rows
      .map(r => ({ r, s: this.scoreText(getText(r), ql) }))
      .filter(x => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .map(x => x.r);
  },

  bindLiveSearch({ input, onSearch, delay = 180 } = {}) {
    if (!input || typeof onSearch !== 'function') return () => {};
    let timer = null;
    let seq = 0;
    const run = () => {
      const my = ++seq;
      clearTimeout(timer);
      timer = setTimeout(() => {
        const result = onSearch(input.value, my);
        if (result && typeof result.then === 'function') {
          result.then(() => {}).catch(() => {});
        }
      }, delay);
    };
    input.addEventListener('input', run);
    input.setAttribute('autocomplete', 'off');
    if (input.type !== 'search') input.type = 'search';
    return () => {
      clearTimeout(timer);
      input.removeEventListener('input', run);
    };
  },

  /**
   * Búsqueda dinámica de paciente por cédula / nombre (API q=).
   * Espera: #m-{field} (hidden id), #m-{field}-q (búsqueda), #m-{field}-res (lista), #m-{field}-chip (selección).
   */
  mountPacienteTypeahead({
    field = 'paciente',
    apiBase = null,
    headers = null,
    minChars = 2,
    limit = 12,
    onSelect = null,
  } = {}) {
    const API = apiBase || (window.DiabCareNav ? DiabCareNav.getApi() : 'http://localhost:8000');
    const getHdr = typeof headers === 'function'
      ? headers
      : () => (headers || (() => {
          const t = localStorage.getItem('token');
          return t ? { Authorization: 'Bearer ' + t } : {};
        })());
    const hidden = document.getElementById('m-' + field);
    const qInput = document.getElementById('m-' + field + '-q');
    const res = document.getElementById('m-' + field + '-res');
    const chip = document.getElementById('m-' + field + '-chip');
    if (!hidden || !qInput || !res) return { clear() {}, setPaciente() {} };

    let seq = 0;
    const esc = (s) => String(s || '').replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));

    const labelPac = (p) => {
      const nom = p.nombre_completo || `${p.nombre || ''} ${p.apellido || ''}`.trim() || 'Paciente';
      const doc = p.documento || 'sin cédula';
      return `${nom} · ${doc}`;
    };

    const pintarChip = (p) => {
      if (!chip) return;
      if (!p) {
        chip.style.display = 'none';
        chip.innerHTML = '';
        return;
      }
      chip.style.display = 'flex';
      chip.innerHTML = `<span>${esc(labelPac(p))}</span><button type="button" class="pac-chip-x" aria-label="Quitar">×</button>`;
      chip.querySelector('.pac-chip-x').onclick = () => {
        hidden.value = '';
        qInput.value = '';
        qInput.style.display = '';
        pintarChip(null);
        res.hidden = true;
        qInput.focus();
      };
      qInput.style.display = 'none';
      res.hidden = true;
    };

    const seleccionar = (p) => {
      if (!p) return;
      hidden.value = p.id_paciente;
      pintarChip(p);
      if (typeof onSelect === 'function') onSelect(p);
    };

    const buscar = async (texto, my) => {
      const q = String(texto || '').trim();
      if (q.length < minChars) {
        res.hidden = true;
        res.innerHTML = '';
        return;
      }
      const r = await fetch(
        `${API}/api/pacientes/?limit=${limit}&q=${encodeURIComponent(q)}&_=${Date.now()}`,
        { headers: getHdr(), cache: 'no-store' }
      );
      if (my !== seq) return;
      if (!r.ok) {
        res.innerHTML = '<div class="pac-suggest-empty">Sin resultados</div>';
        res.hidden = false;
        return;
      }
      const d = await r.json();
      const list = d.pacientes || [];
      if (!list.length) {
        res.innerHTML = '<div class="pac-suggest-empty">Sin coincidencias</div>';
        res.hidden = false;
        return;
      }
      res.innerHTML = list.map(p =>
        `<button type="button" class="pac-suggest-item" data-id="${esc(p.id_paciente)}">
          <strong>${esc(p.documento || '—')}</strong>
          <span>${esc(p.nombre_completo || ((p.nombre || '') + ' ' + (p.apellido || '')).trim())}</span>
        </button>`
      ).join('');
      res.hidden = false;
      res.querySelectorAll('.pac-suggest-item').forEach(btn => {
        btn.onclick = () => {
          const p = list.find(x => String(x.id_paciente) === btn.dataset.id);
          seleccionar(p);
        };
      });
    };

    this.bindLiveSearch({
      input: qInput,
      delay: 200,
      onSearch: (val) => {
        const my = ++seq;
        if (hidden.value && qInput.style.display !== 'none') {
          hidden.value = '';
          pintarChip(null);
          qInput.style.display = '';
        }
        return buscar(val, my);
      },
    });

    qInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { res.hidden = true; }
    });
    document.addEventListener('click', (e) => {
      if (!res.contains(e.target) && e.target !== qInput) res.hidden = true;
    });

    return {
      clear() {
        hidden.value = '';
        qInput.value = '';
        qInput.style.display = '';
        pintarChip(null);
        res.hidden = true;
      },
      async setPaciente(id, labelHint) {
        if (!id) { this.clear(); return; }
        hidden.value = id;
        if (labelHint) {
          pintarChip({ id_paciente: id, nombre_completo: labelHint, documento: '' });
          return;
        }
        try {
          const r = await fetch(`${API}/api/pacientes/${encodeURIComponent(id)}`, { headers: getHdr() });
          if (r.ok) {
            seleccionar(await r.json());
            return;
          }
        } catch (_) {}
        pintarChip({ id_paciente: id, nombre_completo: id, documento: '' });
      },
      setValor(id, labelHint) { return this.setPaciente(id, labelHint); },
    };
  },

  pacienteTypeaheadHtml(field = 'paciente', label = 'Paciente (cédula o nombre)') {
    return `<label class="span-full pac-typeahead-wrap">${label}
      <input type="hidden" id="m-${field}" value="">
      <input class="pac-typeahead-q" type="search" id="m-${field}-q" placeholder="Escribe cédula o nombre…" autocomplete="off">
      <div id="m-${field}-res" class="pac-suggest" hidden></div>
      <div id="m-${field}-chip" class="pac-chip" style="display:none"></div>
    </label>`;
  },

  /**
   * Búsqueda dinámica de medicamento por nombre / principio activo (API q=).
   * Misma estructura DOM que paciente (hidden + q + res + chip).
   */
  mountMedicamentoTypeahead({
    field = 'id_medicamento',
    apiBase = null,
    headers = null,
    minChars = 1,
    limit = 12,
    onSelect = null,
  } = {}) {
    const API = apiBase || (window.DiabCareNav ? DiabCareNav.getApi() : 'http://localhost:8000');
    const getHdr = typeof headers === 'function'
      ? headers
      : () => (headers || (() => {
          const t = localStorage.getItem('token');
          return t ? { Authorization: 'Bearer ' + t } : {};
        })());
    const hidden = document.getElementById('m-' + field);
    const qInput = document.getElementById('m-' + field + '-q');
    const res = document.getElementById('m-' + field + '-res');
    const chip = document.getElementById('m-' + field + '-chip');
    if (!hidden || !qInput || !res) return { clear() {}, setValor() {}, setMedicamento() {} };

    let seq = 0;
    const esc = (s) => String(s || '').replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));

    const labelMed = (m) => {
      const nom = m.nombre || 'Medicamento';
      const pa = m.principio_activo ? ` · ${m.principio_activo}` : '';
      const pvp = m.precio_venta != null && m.precio_venta !== '' ? ` · $${m.precio_venta}` : '';
      return `${nom}${pa}${pvp}`;
    };

    const pintarChip = (m) => {
      if (!chip) return;
      if (!m) {
        chip.style.display = 'none';
        chip.innerHTML = '';
        return;
      }
      chip.style.display = 'flex';
      chip.innerHTML = `<span>${esc(labelMed(m))}</span><button type="button" class="pac-chip-x" aria-label="Quitar">×</button>`;
      chip.querySelector('.pac-chip-x').onclick = () => {
        hidden.value = '';
        qInput.value = '';
        qInput.style.display = '';
        pintarChip(null);
        res.hidden = true;
        qInput.focus();
      };
      qInput.style.display = 'none';
      res.hidden = true;
    };

    const seleccionar = (m) => {
      if (!m) return;
      hidden.value = m.id_medicamento;
      pintarChip(m);
      if (typeof onSelect === 'function') onSelect(m);
    };

    const buscar = async (texto, my) => {
      const q = String(texto || '').trim();
      if (q.length < minChars) {
        res.hidden = true;
        res.innerHTML = '';
        return;
      }
      const r = await fetch(
        `${API}/api/medicamentos?limit=${limit}&q=${encodeURIComponent(q)}&_=${Date.now()}`,
        { headers: getHdr(), cache: 'no-store' }
      );
      if (my !== seq) return;
      if (!r.ok) {
        res.innerHTML = '<div class="pac-suggest-empty">Sin resultados</div>';
        res.hidden = false;
        return;
      }
      const d = await r.json();
      const list = d.medicamentos || [];
      if (!list.length) {
        res.innerHTML = '<div class="pac-suggest-empty">Sin coincidencias</div>';
        res.hidden = false;
        return;
      }
      res.innerHTML = list.map(m =>
        `<button type="button" class="pac-suggest-item" data-id="${esc(m.id_medicamento)}">
          <strong>${esc(m.nombre || '—')}</strong>
          <span>${esc([m.principio_activo, m.forma, m.precio_venta != null && m.precio_venta !== '' ? `PVP $${m.precio_venta}` : ''].filter(Boolean).join(' · ') || 'Catálogo')}</span>
        </button>`
      ).join('');
      res.hidden = false;
      res.querySelectorAll('.pac-suggest-item').forEach(btn => {
        btn.onclick = () => {
          const m = list.find(x => String(x.id_medicamento) === btn.dataset.id);
          seleccionar(m);
        };
      });
    };

    this.bindLiveSearch({
      input: qInput,
      delay: 180,
      onSearch: (val) => {
        const my = ++seq;
        if (hidden.value && qInput.style.display !== 'none') {
          hidden.value = '';
          pintarChip(null);
          qInput.style.display = '';
        }
        return buscar(val, my);
      },
    });

    qInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { res.hidden = true; }
    });
    document.addEventListener('click', (e) => {
      if (!res.contains(e.target) && e.target !== qInput) res.hidden = true;
    });

    const api = {
      clear() {
        hidden.value = '';
        qInput.value = '';
        qInput.style.display = '';
        pintarChip(null);
        res.hidden = true;
      },
      async setMedicamento(id, labelHint) {
        if (!id) { this.clear(); return; }
        hidden.value = id;
        if (labelHint) {
          pintarChip({ id_medicamento: id, nombre: labelHint });
          return;
        }
        try {
          const r = await fetch(`${API}/api/medicamentos/${encodeURIComponent(id)}`, { headers: getHdr() });
          if (r.ok) {
            seleccionar(await r.json());
            return;
          }
        } catch (_) {}
        pintarChip({ id_medicamento: id, nombre: id });
      },
      setValor(id, labelHint) { return this.setMedicamento(id, labelHint); },
    };
    return api;
  },

  medicamentoTypeaheadHtml(field = 'id_medicamento', label = 'Medicamento (nombre o principio)') {
    return `<label class="span-full pac-typeahead-wrap">${label}
      <input type="hidden" id="m-${field}" value="">
      <input class="pac-typeahead-q" type="search" id="m-${field}-q" placeholder="Escribe nombre o principio activo…" autocomplete="off">
      <div id="m-${field}-res" class="pac-suggest" hidden></div>
      <div id="m-${field}-chip" class="pac-chip" style="display:none"></div>
    </label>`;
  },
};

window.authHdr = () => DiabCareAPI.headers();
