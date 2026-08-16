/**
 * DiabCare — iconos clínicos (stroke) + ilustraciones de módulo.
 */
window.DiabCareIcons = {
  _wrap(inner, size) {
    const s = size || 16;
    return `<svg class="ico-svg" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
  },

  svg(name, size) {
    const icons = {
      /* Cabecera / áreas */
      home: '<path d="M3 21h18"/><path d="M5 21V8l7-5 7 5v13"/><path d="M10 14h4"/><path d="M12 12v4"/>',
      estetoscopio: '<path d="M4.8 3.1A.5.5 0 015.5 3H7a1 1 0 011 1v6a4 4 0 108 0V8"/><path d="M6 3v7a6 6 0 0012 0"/><circle cx="20" cy="8" r="2"/>',
      pacientes: '<path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><circle cx="19" cy="8" r="3"/><path d="M19 6.6v2.8M17.6 8h2.8"/>',
      citas: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="M12 14v4M10 16h4"/>',
      mis_citas: '<path d="M4.8 3.1A.5.5 0 015.5 3H7a1 1 0 011 1v6a4 4 0 108 0V8"/><circle cx="20" cy="8" r="2"/><path d="M6 3v7a6 6 0 006 6"/>',
      admisiones: '<path d="M2 20h20"/><path d="M4 20V8h6V4h4v4h6v12"/><path d="M10 12h4"/><path d="M12 10v4"/>',
      urgencias: '<circle cx="12" cy="12" r="10"/><path d="M12 7v10M7 12h10"/>',
      registros: '<rect x="8" y="2" width="12" height="20" rx="2"/><path d="M8 6H6a2 2 0 00-2 2v12a2 2 0 002 2h2"/><path d="M11 10h6M11 14h4"/><path d="M12 18h.01"/>',
      laboratorio: '<path d="M9 3h6"/><path d="M10 3v6.5L4.8 19a2 2 0 001.7 3h10.9a2 2 0 001.8-3L14 9.5V3"/><path d="M7.2 14h9.6"/><circle cx="12" cy="17.5" r="1.2"/>',
      comorbilidades: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0016.5 3c-1.8 0-3 .5-4.5 2C10.5 3.5 9.3 3 7.5 3A5.5 5.5 0 002 8.5c0 2.3 1.5 4 3 5.5l7 7 3-3"/><path d="M3.2 12H8l1.2-2.2L12 16l1.6-4.2 1.2 2.2h5.5"/>',
      diabetes: '<path d="M12 2.7s6.5 6.2 6.5 11.2A6.5 6.5 0 1112 2.7z"/><path d="M12 9v5M10 12h4"/>',
      farmacia: '<path d="m10.5 20.5 10-10a4.95 4.95 0 10-7-7l-10 10a4.95 4.95 0 107 7z"/><path d="m8.5 8.5 7 7"/>',
      recetas: '<path d="M8 3h8a2 2 0 012 2v16l-3-1.5L12 21l-3-1.5L6 21V5a2 2 0 012-2z"/><path d="M9.5 10h2.2c.9 0 1.6.6 1.6 1.4S12.6 13 11.7 13H9.5V16"/><path d="M14.2 10v6"/>',
      facturacion: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M12 14h.01"/>',
      rrhh: '<path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 20v-1a3 3 0 00-2.2-2.9"/><circle cx="16.5" cy="7.5" r="2.5"/><path d="M19 11.2V13M17.8 12.2h2.4"/>',
      analisis: '<path d="M22 12h-4l-3 8L9 4l-3 8H2"/>',
      panel: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/><path d="M12 13h5l-1.2 2 2 3H12"/>',
      prediccion: '<path d="M22 12h-4l-3 8L9 4l-3 8H2"/><circle cx="12" cy="12" r="2"/>',
      reportes: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>',
      pdf: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M9 13h2a1.5 1.5 0 010 3H9v2"/><path d="M14 18v-5h1.3a1.5 1.5 0 010 3H14"/>',
      informes: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
      dataset: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
      pipeline: '<path d="M4 4h6v6H4zM14 14h6v6h-6z"/><path d="M10 7h3a3 3 0 013 3v4"/>',
      modelo: '<circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M8 7.2 10.8 16M16 7.2 13.2 16M8.2 6h7.6"/>',
      usuarios: '<path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>',
      auditoria: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
      configuracion: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9c.3.6.9 1 1.6 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/>',
      corporativo: '<path d="M3 21h18"/><path d="M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6"/>',
      notificaciones: '<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 01-3.4 0"/>',
      sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
      luna: '<path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/>',
      idioma: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10A15.3 15.3 0 0112 2z"/>',
      benchmarking: '<path d="M18 20V10M12 20V4M6 20v-6"/>',
      integraciones: '<path d="M10 13a5 5 0 007.5.5l3-3a5 5 0 00-7-7l-1.8 1.7"/><path d="M14 11a5 5 0 00-7.5-.5l-3 3a5 5 0 007 7l1.8-1.7"/>',
      hospitalizacion: '<path d="M3 21h18"/><path d="M5 21V8l7-5 7 5v13"/><path d="M10 14h4M12 12v4"/>',
      imagenologia: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
      quirofano: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.2 2.2M17.6 17.6l2.2 2.2M2 12h3M19 12h3M4.2 19.8l2.2-2.2M17.6 6.4l2.2-2.2"/>',
      inventario: '<path d="M21 16V8a2 2 0 00-1-1.7l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.7l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>',
      stats: '<path d="M18 20V10M12 20V4M6 20v-6"/>',
      search: '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/>',
      generador: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
      storage: '<path d="M21 16V8a2 2 0 00-1-1.7l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.7l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path d="M3.3 7 12 12l8.7-5M12 22V12"/>',
      logout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
      refresh: '<path d="M23 4v6h-6"/><path d="M20.5 15A9 9 0 1118.4 5.6"/>',
      download: '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
      chevron: '<path d="M9 18l6-6-6-6"/>',
      mail: '<path d="M4 7l8 5 8-5M4 7v10a1 1 0 001 1h14a1 1 0 001-1V7"/>',
      lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 118 0v3"/>',
      health: '<path d="M12 2.7s6.5 6.2 6.5 11.2A6.5 6.5 0 1112 2.7z"/><path d="M12 9v5M10 12h4"/>',
      ml: '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
      box: '<path d="M21 16V8a2 2 0 00-1-1.7l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.7l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>',
      alert: '<path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h16.9a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
      file: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/>',
      server: '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
    };
    return this._wrap(icons[name] || icons.estetoscopio, size);
  },

  nav(modulo) {
    return this.svg(modulo, 16);
  },

  /** Ilustración de cabecera por módulo (no foto de stock). */
  ilustracion(modulo) {
    const key = ({
      pacientes: 'pacientes', citas: 'citas', mis_citas: 'citas',
      admisiones: 'admisiones', urgencias: 'urgencias', registros: 'registros',
      laboratorio: 'laboratorio', comorbilidades: 'corazon',
      farmacia: 'farmacia', recetas: 'recetas', facturacion: 'caja',
      rrhh: 'pacientes', analisis: 'ecg', prediccion: 'ecg', reportes: 'registros',
      pdf: 'registros', panel: 'ecg', diabetes: 'gota',
      dataset: 'lab', pipeline: 'lab', modelo: 'ecg',
      usuarios: 'pacientes', notificaciones: 'avisos',
      auditoria: 'registros', configuracion: 'registros',
    })[modulo] || 'gota';
    const scenes = {
      gota: `
        <ellipse class="art-glow" cx="86" cy="78" rx="52" ry="18"/>
        <path class="art-cyan" d="M86 18c22 28 36 44 36 62a36 36 0 11-72 0c0-18 14-34 36-62z"/>
        <path class="art-ink" d="M86 38c12 16 20 26 20 38a20 20 0 11-40 0c0-12 8-22 20-38z" opacity=".35"/>
        <path class="art-paper" d="M78 72h16M86 64v16" stroke-width="3" fill="none"/>`,
      pacientes: `
        <ellipse class="art-glow" cx="90" cy="96" rx="58" ry="14"/>
        <circle class="art-cyan" cx="70" cy="42" r="18"/>
        <path class="art-cyan" d="M42 96c0-18 12-30 28-30h0c16 0 28 12 28 30"/>
        <circle class="art-deep" cx="118" cy="48" r="14"/>
        <path class="art-paper" d="M118 41v14M111 48h14" stroke-width="2.6" fill="none"/>
        <path class="art-deep" d="M96 96c2-14 12-24 24-24 14 0 24 12 24 24"/>`,
      citas: `
        <rect class="art-cyan" x="38" y="28" width="100" height="78" rx="12"/>
        <rect class="art-ink" x="38" y="28" width="100" height="22" rx="12"/>
        <rect class="art-ink" x="38" y="40" width="100" height="10"/>
        <path class="art-paper" d="M62 24v16M114 24v16" stroke-width="3" fill="none"/>
        <path class="art-paper" d="M88 62v28M74 76h28" stroke-width="3.2" fill="none"/>`,
      urgencias: `
        <circle class="art-cyan" cx="88" cy="64" r="46"/>
        <circle class="art-ink" cx="88" cy="64" r="30"/>
        <path class="art-paper" d="M88 42v44M66 64h44" stroke-width="6" fill="none"/>`,
      admisiones: `
        <rect class="art-deep" x="28" y="70" width="120" height="18" rx="4"/>
        <rect class="art-cyan" x="40" y="48" width="70" height="28" rx="8"/>
        <rect class="art-ink" x="118" y="36" width="18" height="52" rx="3"/>
        <path class="art-paper" d="M48 58h20M58 48v20" stroke-width="2.4" fill="none"/>`,
      laboratorio: `
        <rect class="art-deep" x="44" y="22" width="18" height="70" rx="4"/>
        <rect class="art-cyan" x="48" y="54" width="10" height="34" rx="2"/>
        <rect class="art-deep" x="78" y="18" width="18" height="74" rx="4"/>
        <rect class="art-cyan" x="82" y="48" width="10" height="40" rx="2"/>
        <rect class="art-deep" x="112" y="28" width="18" height="64" rx="4"/>
        <rect class="art-cyan" x="116" y="62" width="10" height="26" rx="2"/>
        <ellipse class="art-glow" cx="96" cy="102" rx="50" ry="10"/>`,
      farmacia: `
        <g transform="rotate(-28 88 64)">
          <rect class="art-cyan" x="40" y="48" width="96" height="36" rx="18"/>
          <rect class="art-ink" x="88" y="48" width="48" height="36" rx="18"/>
        </g>
        <ellipse class="art-glow" cx="90" cy="102" rx="48" ry="10"/>`,
      recetas: `
        <rect class="art-cyan" x="50" y="18" width="76" height="96" rx="8"/>
        <path class="art-paper" d="M66 46h28c8 0 12 6 12 12s-4 12-12 12H66v18" stroke-width="3.2" fill="none"/>
        <path class="art-paper" d="M108 46v48" stroke-width="3.2" fill="none"/>`,
      registros: `
        <rect class="art-cyan" x="52" y="20" width="80" height="92" rx="8"/>
        <rect class="art-ink" x="70" y="14" width="44" height="14" rx="4"/>
        <path class="art-paper" d="M68 54h48M68 70h36M68 86h24" stroke-width="3" fill="none"/>`,
      corazon: `
        <path class="art-cyan" d="M88 108L36 58c-12-14-10-36 12-44 14-5 28 2 40 16 12-14 26-21 40-16 22 8 24 30 12 44z"/>
        <path class="art-paper" d="M40 62h22l8-16 14 36 10-20h28" stroke-width="3.2" fill="none"/>`,
      ecg: `
        <rect class="art-deep" x="24" y="28" width="128" height="72" rx="12"/>
        <path class="art-cyan" d="M36 64h18l8-22 12 44 10-28 8 18h42" stroke-width="3.4" fill="none"/>
        <circle class="art-paper" cx="140" cy="44" r="4"/>`,
      caja: `
        <rect class="art-cyan" x="36" y="36" width="104" height="64" rx="10"/>
        <path class="art-ink" d="M36 56h104" stroke-width="8"/>
        <circle class="art-paper" cx="88" cy="76" r="6"/>`,
      avisos: `
        <path class="art-cyan" d="M88 20c22 0 36 18 36 40 0 28 12 36 12 36H40s12-8 12-36c0-22 14-40 36-40z"/>
        <rect class="art-ink" x="74" y="96" width="28" height="10" rx="5"/>`,
      lab: `
        <path class="art-cyan" d="M70 18h36v28L128 98a14 14 0 01-12 20H60a14 14 0 01-12-20l22-52z"/>
        <path class="art-ink" d="M62 70h52" opacity=".45"/>
        <circle class="art-paper" cx="88" cy="88" r="8"/>`,
    };
    return `<svg class="mod-art" viewBox="0 0 176 120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${scenes[key] || scenes.gota}</svg>`;
  },

  aplicarEnPagina() {
    document.querySelectorAll('[data-icon]').forEach((el) => {
      const name = el.getAttribute('data-icon');
      const size = parseInt(el.getAttribute('data-icon-size') || '16', 10);
      el.innerHTML = this.svg(name, size);
    });
  },
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.DiabCareIcons) DiabCareIcons.aplicarEnPagina();
});
