/**
 * CRUD genérico - sin IDs visibles para el usuario.
 * Los selects se cargan por API; el value interno es el id.
 * Soporta mountTabs({ tabs: [...] }) para varias entidades en una página.
 */
window.DiabCareCrud = {
  _activeMount: 0,
  _unbindSearch: null,

  _tipoTypeahead(def) {
    if (!def) return null;
    if (def.typeahead === 'medicamento' || def.field === 'id_medicamento') return 'medicamento';
    if (def.typeahead === 'paciente' || def.typeahead === true || def.field === 'id_paciente') return 'paciente';
    return null;
  },

  _buildFieldsHtml(fields, lookups) {
    const typeaheadByField = {};
    (lookups || []).forEach(l => {
      const t = DiabCareCrud._tipoTypeahead(l);
      if (t) typeaheadByField[l.field] = t;
    });
    const lookupFields = new Set((lookups || []).map(l => l.field));
    const escAttr = (s) => String(s || '').replace(/"/g, '&quot;');
    return (fields || []).map(f => {
      const span = f.full ? ' class="span-full"' : '';
      const req = f.required ? ' required' : '';
      const label = f.labelUi || f.label || f.key;
      const hint = f.hint
        ? `<small class="field-hint">${f.hint}</small>`
        : '';
      const ph = f.placeholder != null ? ` placeholder="${escAttr(f.placeholder)}"` : '';
      if (typeaheadByField[f.key]) {
        const html = typeaheadByField[f.key] === 'medicamento'
          ? DiabCareAPI.medicamentoTypeaheadHtml(f.key, label)
          : DiabCareAPI.pacienteTypeaheadHtml(f.key, label);
        return hint ? html.replace('</label>', `${hint}</label>`) : html;
      }
      if (lookupFields.has(f.key) || f.as === 'select') {
        let opts = '';
        if (f.options) {
          opts = f.options.map(o => {
            const v = typeof o === 'string' ? o : o.value;
            let t = typeof o === 'string' ? o : o.label;
            if (typeof o === 'string' && window.DiabCareAPI) t = DiabCareAPI.capLabel(t);
            return `<option value="${v}">${t}</option>`;
          }).join('');
        }
        const empty = f.options
          ? ''
          : `<option value="">${escAttr(f.placeholder || '- Seleccione -')}</option>`;
        return `<label${span}>${label}<select id="m-${f.key}"${req}>${empty}${opts}</select>${hint}</label>`;
      }
      if (f.as === 'textarea') {
        return `<label${span}>${label}<textarea id="m-${f.key}" rows="2"${ph}${req}></textarea>${hint}</label>`;
      }
      const type = f.type === 'number' ? 'number' : (f.type === 'date' ? 'date' : 'text');
      const step = f.type === 'number' ? ' step="0.01"' : '';
      const def = f.default != null ? ` value="${f.default}"` : '';
      return `<label${span}>${label}<input id="m-${f.key}" type="${type}"${step}${def}${ph}${req}>${hint}</label>`;
    }).join('\n');
  },

  async mount(cfg) {
    const API = DiabCareNav.getApi();
    const token = localStorage.getItem('token');
    const hdr = () => {
      const h = { 'Content-Type': 'application/json' };
      const t = localStorage.getItem('token');
      if (t && t !== 'sesion' && t !== 'null' && t !== 'undefined') {
        h.Authorization = 'Bearer ' + t;
      }
      return h;
    };
    // Reusar id preasignado por mountTabs (evita doble ++ que cancela el propio mount).
    const mountId = cfg.__mountId != null ? cfg.__mountId : (++DiabCareCrud._activeMount);
    let rows = [];
    let allRows = [];
    let pag = 1;
    let totalRows = 0;
    const pageSize = cfg.pageSize
      || (cfg.viewMode === 'table' ? 20 : (window.DiabCareAPI?.GRID_PAGE_SIZE || 12));
    const lookups = {};

    function toast(msg, type = 'success') {
      const t = document.getElementById('toast');
      if (!t) return alert(msg);
      document.getElementById('t-msg').textContent = msg;
      document.getElementById('t-icon').textContent = type === 'success' ? '✓' : '✗';
      t.className = `toast ${type} show`;
      setTimeout(() => t.classList.remove('show'), 3000);
    }

    function sigueActivo() {
      return mountId === DiabCareCrud._activeMount;
    }

    function labelDe(campo, id) {
      if (!id && id !== 0) return '-';
      const map = lookups[campo];
      if (map && map[String(id)]) return map[String(id)];
      return '-';
    }

    async function fetchConTimeout(url, ms = 12000) {
      const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timer = ctrl ? setTimeout(() => ctrl.abort(), ms) : null;
      try {
        return await fetch(url, {
          headers: hdr(),
          cache: 'no-store',
          credentials: 'include',
          signal: ctrl ? ctrl.signal : undefined,
        });
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    async function cargarLookup(def) {
      try {
        const tipoTa = DiabCareCrud._tipoTypeahead(def);
        // Typeahead busca bajo demanda: no bloquear montaje con precargas grandes.
        if (tipoTa && def.preload !== true) {
          lookups[def.field] = lookups[def.field] || {};
          return;
        }
        const r = await fetchConTimeout(`${API}${def.url}`, 10000);
        if (!r.ok || !sigueActivo()) return;
        const d = await r.json();
        const list = d[def.listKey] || d.datos || (Array.isArray(d) ? d : []);
        const map = lookups[def.field] || {};
        const sel = document.getElementById('m-' + def.field);
        if (sel && !tipoTa) {
          sel.innerHTML = '<option value="">- Seleccione -</option>';
          list.forEach(item => {
            const id = String(item[def.idKey]);
            const label = typeof def.label === 'function'
              ? def.label(item)
              : String(item[def.labelKey] || id);
            map[id] = label;
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = label;
            sel.appendChild(opt);
          });
        } else {
          list.forEach(item => {
            map[String(item[def.idKey])] = typeof def.label === 'function'
              ? def.label(item)
              : String(item[def.labelKey] || item[def.idKey]);
          });
        }
        lookups[def.field] = map;
      } catch (e) {
        console.warn('lookup', def.field, e);
        lookups[def.field] = lookups[def.field] || {};
      }
    }

    async function cargarLookups() {
      const defs = cfg.lookups || [];
      await Promise.all(defs.map(def => {
        if (!sigueActivo()) return Promise.resolve();
        return cargarLookup(def);
      }));
    }

    /** Rellena etiquetas de typeahead sin bloquear (nombres en tabla). */
    async function enriquecerTypeaheadLabels() {
      const defs = (cfg.lookups || []).filter(d => DiabCareCrud._tipoTypeahead(d));
      if (!defs.length || !sigueActivo()) return;
      await Promise.all(defs.map(async (def) => {
        try {
          const r = await fetchConTimeout(`${API}${def.url}`, 10000);
          if (!r.ok || !sigueActivo()) return;
          const d = await r.json();
          const list = d[def.listKey] || d.datos || (Array.isArray(d) ? d : []);
          const map = lookups[def.field] || (lookups[def.field] = {});
          list.forEach(item => {
            map[String(item[def.idKey])] = typeof def.label === 'function'
              ? def.label(item)
              : String(item[def.labelKey] || item[def.idKey]);
          });
        } catch (e) {
          console.warn('enrich', def.field, e);
        }
      }));
      if (sigueActivo()) render();
    }

    function celda(row, col) {
      if (col.render) return col.render(row);
      if (col.lookup) return labelDe(col.lookup, row[col.key]);
      if (col.hideId) return labelDe(col.key, row[col.key]);
      const key = String(col.key || '');
      if (key === 'estado' && row.estado_label) return row.estado_label;
      if (key === 'tipo' && row.tipo_label) return row.tipo_label;
      const v = row[col.key];
      const isMoney = /precio|monto|total|costo|iva|descuento|neto|bruto|esperado|contado|diferencia|pendiente|pvp/i.test(key);
      if (isMoney && v != null && v !== '') {
        const n = Number(v);
        if (Number.isFinite(n)) return window.DiabCareAPI ? DiabCareAPI.moneyFmt(n) : n.toFixed(2);
      }
      if (v === true || v === 'true' || v === 1 || v === '1') return 'Sí';
      if (v === false || v === 'false') return 'No';
      if (v != null && v !== '' && /^(estado|activo|metodo|tipo|desenlace)$/i.test(key)) {
        return window.DiabCareAPI ? DiabCareAPI.capLabel(v) : v;
      }
      if (typeof v === 'string' && /^[a-záéíóúüñ_]+$/i.test(v) && v === v.toLowerCase() && v.length > 2) {
        const known = /^(programada|confirmada|atendida|cancelada|vigente|pagada|anulada|anulado|cerrado|abierto|emitida|emitido|registrada|registrado|pendiente|activo|inactiva|inactivo|alta|dispensada|dispensado|no_asistio)$/i;
        if (known.test(v) || v.includes('_')) {
          return window.DiabCareAPI ? DiabCareAPI.capLabel(v) : v;
        }
      }
      return (v ?? '-');
    }

    function textoBusqueda(row) {
      const cols = (cfg.columns || []).filter(c => !c.internal);
      const parts = cols.map(c => String(celda(row, c) || ''));
      Object.values(row || {}).forEach(v => {
        if (v != null && typeof v !== 'object') parts.push(String(v));
      });
      return parts.join(' ');
    }

    function asegurarBuscador() {
      if (cfg.hideSearch) return null;
      let input = document.getElementById('crud-live-search');
      if (input) return input;
      const card = document.querySelector('.tabla-card');
      if (!card) return null;
      let top = card.querySelector('.tabla-top');
      if (!top) {
        top = document.createElement('div');
        top.className = 'tabla-top';
        card.insertBefore(top, card.firstChild);
      }
      input = document.createElement('input');
      input.className = 'search';
      input.id = 'crud-live-search';
      input.type = 'search';
      input.autocomplete = 'off';
      input.placeholder = cfg.searchPlaceholder || 'Escribe para filtrar…';
      input.style.minWidth = '220px';
      input.style.flex = '1';
      top.prepend(input);
      return input;
    }

    function aplicarFiltroLocal() {
      if (!sigueActivo()) return;
      pag = 1;
      return cargar();
    }

    function pintarPager() {
      if (!sigueActivo() || !window.DiabCareAPI) return;
      const host = DiabCareAPI.ensurePagerHost({ id: 'crudPager' });
      DiabCareAPI.renderPager(host, {
        page: pag,
        pageSize,
        total: totalRows,
        onPage: (p) => {
          if (!sigueActivo()) return;
          pag = p;
          cargar();
        },
      });
    }

    async function cargar() {
      if (!sigueActivo()) return;
      const bodyEl = document.getElementById('tablaBody');
      const input = document.getElementById('crud-live-search');
      const q = input ? input.value.trim() : '';
      let base = cfg.listUrl || '';
      if (!base) {
        if (bodyEl) bodyEl.innerHTML = '<div class="loading">Sin URL de listado configurada</div>';
        return;
      }
      const rel = window.DiabCareAPI
        ? DiabCareAPI.listUrlWithPage(base, {
            page: pag,
            pageSize,
            q,
            offsetParam: cfg.offsetParam || 'offset',
          })
        : (() => {
            const sep = base.includes('?') ? '&' : '?';
            return `${base}${sep}limit=${pageSize}&offset=${(pag - 1) * pageSize}${q ? `&q=${encodeURIComponent(q)}` : ''}&_=${Date.now()}`;
          })();
      const url = `${API}${rel}`;
      try {
        const r = await fetchConTimeout(url, 20000);
        if (!sigueActivo()) return;
        if (r.status === 401) { DiabCareNav.irLogin(); return; }
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          if (bodyEl) {
            bodyEl.innerHTML = `<div class="loading">No se pudo cargar (${r.status}): ${String(err.detail || err.error || 'error de API')}</div>`;
          }
          pintarPager();
          return;
        }
        const d = await r.json();
        if (!sigueActivo()) return;
        allRows = d[cfg.listKey] || d.datos || (Array.isArray(d) ? d : []);
        if (cfg.rowFilter) allRows = allRows.filter(cfg.rowFilter);
        const reported = Number(d.total);
        if (Number.isFinite(reported) && reported >= 0) {
          totalRows = reported;
        } else {
          const offset = (pag - 1) * pageSize;
          totalRows = allRows.length < pageSize
            ? offset + allRows.length
            : offset + allRows.length + 1;
        }
        const maxPag = Math.max(1, Math.ceil(totalRows / pageSize) || 1);
        if (pag > maxPag && totalRows > 0) {
          pag = maxPag;
          return cargar();
        }
        rows = allRows.slice();
        render();
        pintarPager();
        if (cfg.onLoaded) cfg.onLoaded(rows, lookups);
      } catch (e) {
        if (!sigueActivo()) return;
        const msg = (e && e.name === 'AbortError')
          ? 'Tiempo de espera agotado. Revise MinIO / API e intente de nuevo.'
          : ('Error de red: ' + (e && e.message ? e.message : 'desconocido'));
        if (bodyEl) bodyEl.innerHTML = `<div class="loading">${msg}</div>`;
        pintarPager();
      }
    }

    function render() {
      if (!sigueActivo()) return;
      const body = document.getElementById('tablaBody');
      if (!body) return;
      const cols = (cfg.columns || []).filter(c => !c.internal);
      const input = document.getElementById('crud-live-search');
      const q = input ? input.value.trim() : '';
      if (!rows.length) {
        body.innerHTML = q
          ? `<div class="loading">Sin coincidencias para “${q.replace(/[<>&]/g, '')}”</div>`
          : '<div class="loading">Sin registros</div>';
        return;
      }

      const useTable = cfg.viewMode === 'table';
      if (!useTable && window.DiabCareAPI && DiabCareAPI.buildDataGrid) {
        body.innerHTML = DiabCareAPI.buildDataGrid({
          rows,
          columns: cols.map(c => ({
            key: c.key,
            label: c.label,
            title: c.title,
            badge: c.badge,
            render: (row) => celda(row, c),
          })),
          idField: cfg.idField,
          actionsHtml: (row, id) => {
            let a = '';
            (cfg.rowActions || []).forEach(act => {
              if (typeof act.show === 'function' && !act.show(row)) return;
              a += `<button type="button" class="btn btn-ghost btn-sm" data-act="${act.id}" data-id="${id}">${act.label}</button>`;
            });
            if (!cfg.hideEdit && !cfg.readOnly) {
              a += `<button type="button" class="btn btn-ghost btn-sm" data-edit="${id}">Editar</button>`;
            }
            if (!cfg.hideDelete && !cfg.readOnly) {
              a += `<button type="button" class="btn btn-ghost btn-sm" data-del="${id}">Eliminar</button>`;
            }
            return a;
          },
        });
      } else {
        let h = '<table class="tabla"><thead><tr>';
        cols.forEach(c => { h += `<th>${c.label}</th>`; });
        h += '<th></th></tr></thead><tbody>';
        rows.forEach(row => {
          const id = row[cfg.idField];
          h += '<tr>';
          cols.forEach(c => { h += `<td>${celda(row, c)}</td>`; });
          h += '<td class="td-actions">';
          (cfg.rowActions || []).forEach(a => {
            if (typeof a.show === 'function' && !a.show(row)) return;
            h += `<button type="button" class="btn btn-ghost btn-sm" data-act="${a.id}" data-id="${id}">${a.label}</button> `;
          });
          if (!cfg.hideEdit && !cfg.readOnly) {
            h += `<button type="button" class="btn btn-ghost btn-sm" data-edit="${id}">Editar</button> `;
          }
          if (!cfg.hideDelete && !cfg.readOnly) {
            h += `<button type="button" class="btn btn-ghost btn-sm" data-del="${id}">Eliminar</button>`;
          }
          h += '</td></tr>';
        });
        h += '</tbody></table>';
        body.innerHTML = h;
      }

      body.querySelectorAll('[data-edit]').forEach(b => {
        b.onclick = () => abrir(rows.find(x => String(x[cfg.idField]) === b.dataset.edit));
      });
      body.querySelectorAll('[data-del]').forEach(b => {
        b.onclick = () => eliminar(b.dataset.del);
      });
      body.querySelectorAll('[data-act]').forEach(b => {
        const act = (cfg.rowActions || []).find(a => a.id === b.dataset.act);
        if (act) {
          b.onclick = () => act.onClick(rows.find(x => String(x[cfg.idField]) === b.dataset.id), { toast, cargar, API, hdr });
        }
      });
    }

    const typeaheadCtl = {};

    function asegurarTypeaheads() {
      (cfg.lookups || []).forEach(def => {
        const tipo = DiabCareCrud._tipoTypeahead(def);
        if (!tipo) return;
        if (typeaheadCtl[def.field]) return;
        typeaheadCtl[def.field] = tipo === 'medicamento'
          ? DiabCareAPI.mountMedicamentoTypeahead({
              field: def.field,
              onSelect: (m) => {
                const map = lookups[def.field] || (lookups[def.field] = {});
                map[String(m.id_medicamento)] = m.nombre || String(m.id_medicamento);
              },
            })
          : DiabCareAPI.mountPacienteTypeahead({ field: def.field });
      });
    }

    function abrir(row) {
      if ((cfg.readOnly || cfg.hideCreate) && !row) return;
      document.getElementById('modal').style.display = 'flex';
      document.getElementById('modal-titulo').textContent = row ? (cfg.editTitle || 'Editar') : (cfg.createTitle || 'Nuevo');
      const fid = document.getElementById('f-id');
      if (fid) fid.value = row ? row[cfg.idField] : '';
      asegurarTypeaheads();
      (cfg.fields || []).forEach(f => {
        const el = document.getElementById('m-' + f.key);
        if (!el) return;
        const val = row ? (row[f.key] ?? f.default ?? '') : (f.default ?? '');
        if (typeaheadCtl[f.key]) {
          if (val) {
            const hint = lookups[f.key] ? lookups[f.key][String(val)] : '';
            const ctl = typeaheadCtl[f.key];
            if (ctl.setValor) ctl.setValor(val, hint);
            else if (ctl.setMedicamento) ctl.setMedicamento(val, hint);
            else ctl.setPaciente(val, hint);
          } else {
            typeaheadCtl[f.key].clear();
            setTimeout(() => {
              const qEl = document.getElementById('m-' + f.key + '-q');
              if (qEl) qEl.focus();
            }, 50);
          }
          return;
        }
        if (el.tagName === 'SELECT') {
          el.value = String(val);
        } else if (el.type === 'checkbox') {
          el.checked = val === true || val === 'true' || val === 1 || val === '1';
        } else {
          el.value = val;
        }
      });
    }

    function cerrar() { document.getElementById('modal').style.display = 'none'; }

    async function guardar() {
      const id = document.getElementById('f-id')?.value || '';
      const body = {};
      (cfg.fields || []).forEach(f => {
        const el = document.getElementById('m-' + f.key);
        if (!el) return;
        let v = el.type === 'checkbox' ? el.checked : el.value;
        if (f.type === 'number') v = parseFloat(v) || 0;
        if (f.type === 'bool') v = el.type === 'checkbox' ? el.checked : (v === 'true' || v === '1');
        if (f.required && (v === '' || v == null)) {
          const tipo = (cfg.lookups || []).find(l => l.field === f.key);
          const kind = DiabCareCrud._tipoTypeahead(tipo);
          body.__err = typeaheadCtl[f.key]
            ? (kind === 'medicamento'
              ? `Busque y seleccione ${f.labelUi || f.label || f.key}`
              : `Busque y seleccione ${f.labelUi || f.label || f.key} por cédula`)
            : `Seleccione ${f.labelUi || f.label || f.key}`;
        }
        body[f.key] = v;
      });
      if (body.__err) { toast(body.__err, 'error'); delete body.__err; return; }
      if (cfg.beforeSave) {
        const extra = cfg.beforeSave(body);
        if (extra && extra.error) { toast(extra.error, 'error'); return; }
      }
      const url = id ? `${API}${cfg.itemUrl(id)}` : `${API}${cfg.createUrl || cfg.listUrl}`;
      const method = id ? 'PUT' : 'POST';
      const btn = document.querySelector('#modal .btn-primary');
      if (btn) { btn.disabled = true; btn.dataset._lbl = btn.textContent; btn.textContent = 'Guardando...'; }
      try {
        const r = await fetch(url, { method, headers: hdr(), body: JSON.stringify(body), credentials: 'include' });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) {
          const detail = typeof d.detail === 'string' ? d.detail
            : (Array.isArray(d.detail) ? d.detail.map(x => (x && x.msg) || x).join('; ') : '');
          toast(detail || d.error || `Error al guardar (${r.status})`, 'error');
          return;
        }
        cerrar();
        toast(id ? 'Actualizado' : 'Creado');
        if (typeof cfg.afterSave === 'function') {
          try { cfg.afterSave(d, body); } catch (_) { /* ignore */ }
        }
        cargar();
      } catch (_) {
        toast('Error de conexión. ¿Backend / MinIO activos?', 'error');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = btn.dataset._lbl || 'Guardar';
          delete btn.dataset._lbl;
        }
      }
    }

    async function eliminar(id) {
      const ok = window.DiabCareAPI && DiabCareAPI.confirm
        ? await DiabCareAPI.confirm({
            title: 'Eliminar registro',
            message: '¿Eliminar este registro? Esta acción no se puede deshacer.',
            confirmLabel: 'Eliminar',
            cancelLabel: 'Cancelar',
            danger: true,
          })
        : window.confirm('¿Eliminar este registro?');
      if (!ok) return;
      const r = await fetch(`${API}${cfg.itemUrl(id)}`, { method: 'DELETE', headers: hdr(), credentials: 'include' });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { toast(d.detail || d.error || 'Error', 'error'); return; }
      toast('Eliminado');
      cargar();
    }

    window.abrirModal = () => abrir(null);
    window.cerrarModal = cerrar;
    window.guardarCrud = guardar;
    if (cfg.seedUrl) {
      window.seedModulo = async () => {
        await fetch(`${API}${cfg.seedUrl}`, { method: 'POST', headers: hdr(), credentials: 'include' });
        toast('Catálogo listo');
        await enriquecerTypeaheadLabels();
        if (sigueActivo()) cargar();
      };
    } else {
      window.seedModulo = undefined;
    }

    const readOnly = !!cfg.readOnly;
    if (readOnly) {
      cfg.hideEdit = true;
      cfg.hideDelete = true;
      cfg.hideCreate = true;
      const newBtn = document.querySelector('.page-header .btn-primary');
      if (newBtn) newBtn.style.display = 'none';
      const saveBtn = document.querySelector('#modal .modal-footer .btn-primary');
      if (saveBtn) saveBtn.style.display = 'none';
    }

    if (!sigueActivo()) return { cargar, toast, lookups, abrir, aplicarFiltroLocal, stale: true, mountId };

    const searchInput = asegurarBuscador();
    if (searchInput) {
      searchInput.placeholder = cfg.searchPlaceholder || 'Escribe para filtrar…';
      if (typeof DiabCareCrud._unbindSearch === 'function') {
        DiabCareCrud._unbindSearch();
        DiabCareCrud._unbindSearch = null;
      }
      if (window.DiabCareAPI) {
        DiabCareCrud._unbindSearch = DiabCareAPI.bindLiveSearch({
          input: searchInput,
          delay: 160,
          onSearch: () => {
            if (!sigueActivo()) return;
            pag = 1;
            return cargar();
          },
        });
      }
    }

    // Selects clásicos (no typeahead) en paralelo; la tabla no espera etiquetas typeahead.
    await cargarLookups();
    if (!sigueActivo()) return { cargar, toast, lookups, abrir, aplicarFiltroLocal, stale: true, mountId };

    await cargar();
    if (sigueActivo()) {
      // Nombres de medicamento/paciente en columnas: en segundo plano.
      enriquecerTypeaheadLabels().catch(() => {});
    }
    return { cargar, toast, lookups, abrir, aplicarFiltroLocal, mountId };
  },

  /**
   * tabs: [{ id, label, fieldsHtml?, ...mountCfg }]
   */
  async mountTabs(opts) {
    const tabs = opts.tabs || [];
    const bar = document.getElementById(opts.tabBarId || 'crudTabs');
    const fieldsHost = document.getElementById(opts.fieldsHostId || 'modalFields');
    const seedBtn = document.getElementById(opts.seedBtnId || 'btnSeed');
    const extraBtn = document.getElementById(opts.extraBtnId || 'btnExtra');
    let activo = null;
    let handle = null;
    let seq = 0;

    function paintTabs() {
      if (!bar) return;
      bar.innerHTML = tabs.map(t =>
        `<button type="button" class="btn btn-sm ${t.id === activo ? 'btn-primary' : 'btn-ghost'}" data-tab="${t.id}">${t.label}</button>`
      ).join(' ');
      bar.querySelectorAll('[data-tab]').forEach(b => {
        b.onclick = () => { switchTab(b.dataset.tab); };
      });
    }

    async function switchTab(id) {
      const tab = tabs.find(t => t.id === id);
      if (!tab) return;
      if (id === activo && handle && !handle.stale) return;

      const my = ++seq;
      activo = id;
      // Un solo ++: cancela mounts previos y se pasa a mount (sin segundo ++).
      const mountId = ++DiabCareCrud._activeMount;
      paintTabs();

      const search = document.getElementById('crud-live-search');
      if (search) search.value = '';
      const body = document.getElementById('tablaBody');
      if (body) {
        if (window.DiabCareSkeleton && DiabCareSkeleton.paintInto) {
          DiabCareSkeleton.paintInto(body);
        } else {
          body.innerHTML = '<div class="loading"><div class="spinner"></div>Cargando…</div>';
        }
      }

      if (fieldsHost) {
        fieldsHost.innerHTML = tab.fieldsHtml || DiabCareCrud._buildFieldsHtml(tab.fields, tab.lookups);
        if (!document.getElementById('f-id')) {
          fieldsHost.insertAdjacentHTML('afterbegin', '<input type="hidden" id="f-id">');
        }
      }
      if (seedBtn) {
        seedBtn.style.display = (tab.seedUrl && !tab.readOnly) ? '' : 'none';
      }
      if (extraBtn) {
        if (tab.extraBtn) {
          extraBtn.style.display = '';
          extraBtn.textContent = tab.extraBtn.label;
          extraBtn.onclick = () => tab.extraBtn.onClick();
        } else {
          extraBtn.style.display = 'none';
        }
      }
      const newBtn = document.querySelector('.page-header .btn-primary');
      if (newBtn) {
        const hide = tab.hideCreate || tab.readOnly || (tab.fields && tab.fields.length === 0);
        newBtn.style.display = hide ? 'none' : '';
      }
      const sub = document.getElementById('pageSub');
      if (sub && tab.sub) sub.textContent = tab.sub;

      try {
        const next = await DiabCareCrud.mount({ ...tab, __mountId: mountId });
        if (my !== seq) return;
        handle = next;
        if (opts.onTab && typeof opts.onTab === 'function') {
          try { opts.onTab(tab, handle); } catch (_) {}
        }
      } catch (e) {
        console.error('mountTabs', e);
        if (my !== seq) return;
        if (body) {
          body.innerHTML = `<div class="loading">Error al cargar la pestaña: ${String(e && e.message ? e.message : e)}</div>`;
        }
      }
    }

    paintTabs();
    if (tabs[0]) await switchTab(tabs[0].id);
    return {
      switchTab,
      getHandle: () => handle,
    };
  },
};
