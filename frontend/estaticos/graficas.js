/**
 * Gráficas canvas locales (sin CDN) para el módulo de análisis.
 */
(function (w) {
  // Los colores salen de los tokens del tema: asi el mismo grafico cambia con
  // claro/oscuro y no se cuela la paleta vieja de Tailwind saturado.
  function tono(nombre, respaldo) {
    try {
      const v = getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
      return v || respaldo;
    } catch (_) {
      return respaldo;
    }
  }
  const PAL_FB = ['#8FB4BE', '#C4A06A', '#6B9A7A', '#C46B6B', '#A98D72', '#8DA79F', '#B3D0D6'];
  const TOKENS = ['--dc-info', '--dc-alerta', '--dc-ok', '--dc-riesgo', '--dc-arena', '--dc-violeta', '--accent2'];
  const PAL = new Proxy([], {
    get(_t, k) {
      if (k === 'length') return TOKENS.length;
      const i = Number(k);
      if (Number.isInteger(i)) return tono(TOKENS[i % TOKENS.length], PAL_FB[i % PAL_FB.length]);
      return undefined;
    },
  });
  // Atajos por rol clinico, para no repetir el nombre del token en cada pagina.
  const ROL = {
    get riesgo() { return tono('--dc-riesgo', '#C46B6B'); },
    get ok() { return tono('--dc-ok', '#6B9A7A'); },
    get alerta() { return tono('--dc-alerta', '#C4A06A'); },
    get info() { return tono('--dc-info', '#8FB4BE'); },
  };

  function css(name, fallback) {
    try {
      const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    } catch (_) {
      return fallback;
    }
  }

  function ink() { return css('--text', '#E6E2DC'); }
  function muted() { return css('--text2', '#C5CDD1'); }
  function grid() { return css('--border', 'rgba(230,226,220,0.22)'); }

  function prep(canvas, h) {
    if (!canvas) return null;
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const wdt = Math.max(120, canvas.clientWidth || canvas.parentElement?.clientWidth || 320);
    const hgt = Math.max(120, h || canvas.clientHeight || 200);
    canvas.width = Math.round(wdt * dpr);
    canvas.height = Math.round(hgt * dpr);
    canvas.style.width = wdt + 'px';
    canvas.style.height = hgt + 'px';
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, wdt, hgt);
    return { ctx, w: wdt, h: hgt };
  }

  function maxOf(arr) {
    let m = 0;
    for (const v of arr) m = Math.max(m, Number(v) || 0);
    return m || 1;
  }

  function doughnut(canvas, labels, values, colors) {
    const g = prep(canvas, 200);
    if (!g) return;
    const { ctx, w, h } = g;
    const total = values.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
    const cx = w * 0.38;
    const cy = h / 2;
    const r = Math.min(cx, cy) - 12;
    let a = -Math.PI / 2;
    values.forEach((v, i) => {
      const slice = (Number(v) || 0) / total * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, a, a + slice);
      ctx.closePath();
      ctx.fillStyle = (colors && colors[i]) || PAL[i % PAL.length];
      ctx.fill();
      a += slice;
    });
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.55, 0, Math.PI * 2);
    ctx.fillStyle = css('--uv-card', css('--card', '#27363B'));
    ctx.fill();
    ctx.fillStyle = ink();
    ctx.font = '700 16px Figtree, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(String(Math.round(total)).replace(/\B(?=(\d{3})+(?!\d))/g, '.'), cx, cy + 5);

    let ly = 18;
    ctx.textAlign = 'left';
    ctx.font = '600 12px Figtree, sans-serif';
    labels.forEach((lab, i) => {
      const pct = ((Number(values[i]) || 0) / total * 100).toFixed(1);
      ctx.fillStyle = (colors && colors[i]) || PAL[i % PAL.length];
      ctx.fillRect(w * 0.68, ly, 10, 10);
      ctx.fillStyle = ink();
      ctx.fillText(`${lab}  ${pct}%`, w * 0.68 + 16, ly + 10);
      ly += 22;
    });
  }

  function bars(canvas, labels, series, opts) {
    const g = prep(canvas, (opts && opts.height) || 220);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: 36, r: 12, t: 16, b: 36 };
    const innerW = w - pad.l - pad.r;
    const innerH = h - pad.t - pad.b;
    const n = labels.length || 1;
    const groups = Array.isArray(series[0]) ? series : [series];
    const flat = groups.flat();
    const mx = maxOf(flat);
    const gw = innerW / n;
    const bw = Math.max(6, (gw - 8) / groups.length);

    ctx.strokeStyle = grid();
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t);
    ctx.lineTo(pad.l, h - pad.b);
    ctx.lineTo(w - pad.r, h - pad.b);
    ctx.stroke();

    ctx.fillStyle = muted();
    ctx.font = '600 10px IBM Plex Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText(String(Math.round(mx)), pad.l - 4, pad.t + 8);

    groups.forEach((vals, gi) => {
      ctx.fillStyle = (opts && opts.colors && opts.colors[gi]) || PAL[gi % PAL.length];
      vals.forEach((v, i) => {
        const hh = (Number(v) || 0) / mx * innerH;
        const x = pad.l + i * gw + 4 + gi * bw;
        const y = h - pad.b - hh;
        ctx.fillRect(x, y, bw - 2, hh);
      });
    });

    ctx.fillStyle = muted();
    ctx.font = '600 10px Figtree, sans-serif';
    ctx.textAlign = 'center';
    labels.forEach((lab, i) => {
      ctx.fillText(String(lab).slice(0, 10), pad.l + i * gw + gw / 2, h - 10);
    });
  }

  function line(canvas, labels, values, color) {
    const g = prep(canvas, 220);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: 36, r: 12, t: 16, b: 36 };
    const innerW = w - pad.l - pad.r;
    const innerH = h - pad.t - pad.b;
    const n = Math.max(1, values.length - 1);
    const mx = maxOf(values);
    const col = color || PAL[0];

    ctx.strokeStyle = grid();
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t);
    ctx.lineTo(pad.l, h - pad.b);
    ctx.lineTo(w - pad.r, h - pad.b);
    ctx.stroke();

    ctx.beginPath();
    values.forEach((v, i) => {
      const x = pad.l + (i / n) * innerW;
      const y = h - pad.b - ((Number(v) || 0) / mx) * innerH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = col;
    ctx.lineWidth = 2.2;
    ctx.stroke();

    ctx.fillStyle = muted();
    ctx.font = '600 10px Figtree, sans-serif';
    ctx.textAlign = 'center';
    const step = labels.length > 8 ? Math.ceil(labels.length / 8) : 1;
    labels.forEach((lab, i) => {
      if (i % step) return;
      const x = pad.l + (i / n) * innerW;
      ctx.fillText(String(lab), x, h - 10);
    });
  }

  /**
   * Dispersión de dos variables clínicas, un punto por paciente.
   * `puntos`: [{x, y, g}] donde g=1 marca la cohorte con diabetes.
   * Es la vista que separa de verdad las dos poblaciones: una barra promedia
   * y esconde justamente la nube de riesgo metabólico.
   */
  function scatter(canvas, puntos, opts) {
    const o = opts || {};
    const g = prep(canvas, o.height || 240);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: 40, r: 14, t: 16, b: 38 };
    const innerW = w - pad.l - pad.r;
    const innerH = h - pad.t - pad.b;
    const xs = puntos.map((p) => Number(p.x) || 0);
    const ys = puntos.map((p) => Number(p.y) || 0);
    const xMax = o.xMax || maxOf(xs);
    const yMax = o.yMax || maxOf(ys);
    const colDm = o.colorDm || ROL.riesgo;
    const colNo = o.colorNo || ROL.ok;

    ctx.strokeStyle = grid();
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t);
    ctx.lineTo(pad.l, h - pad.b);
    ctx.lineTo(w - pad.r, h - pad.b);
    ctx.stroke();

    // Umbral clínico horizontal (p. ej. HbA1c 6,5 %)
    if (o.umbralY) {
      const y = h - pad.b - (o.umbralY / yMax) * innerH;
      ctx.save();
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = ROL.riesgo;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(w - pad.r, y);
      ctx.stroke();
      ctx.restore();
      ctx.fillStyle = ROL.riesgo;
      ctx.font = '600 9px IBM Plex Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(o.umbralLabel || String(o.umbralY), pad.l + 4, y - 3);
    }

    puntos.forEach((p) => {
      const x = pad.l + ((Number(p.x) || 0) / xMax) * innerW;
      const y = h - pad.b - ((Number(p.y) || 0) / yMax) * innerH;
      ctx.beginPath();
      ctx.arc(x, y, 2.6, 0, Math.PI * 2);
      ctx.fillStyle = Number(p.g) === 1 ? colDm : colNo;
      ctx.globalAlpha = 0.55;
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    ctx.fillStyle = muted();
    ctx.font = '600 10px Figtree, sans-serif';
    ctx.textAlign = 'center';
    if (o.xLabel) ctx.fillText(o.xLabel, pad.l + innerW / 2, h - 8);
    ctx.textAlign = 'right';
    ctx.font = '600 10px IBM Plex Mono, monospace';
    ctx.fillText(String(Math.round(yMax)), pad.l - 4, pad.t + 8);
    ctx.fillText('0', pad.l - 4, h - pad.b);
    if (o.yLabel) {
      ctx.save();
      ctx.translate(11, pad.t + innerH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.fillStyle = muted();
      ctx.font = '600 10px Figtree, sans-serif';
      ctx.fillText(o.yLabel, 0, 0);
      ctx.restore();
    }
  }

  /**
   * Curvas de distribución superpuestas (DM+ vs DM-) con relleno.
   * Un histograma en barras agrupadas obliga a comparar alturas vecinas;
   * dos áreas encimadas muestran de un vistazo el desplazamiento entre cohortes.
   */
  function areas(canvas, labels, series, opts) {
    const o = opts || {};
    const g = prep(canvas, o.height || 220);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: 40, r: 14, t: 16, b: 36 };
    const innerW = w - pad.l - pad.r;
    const innerH = h - pad.t - pad.b;
    const n = Math.max(1, labels.length - 1);
    const mx = maxOf(series.flat());
    const cols = o.colors || [ROL.riesgo, ROL.ok];

    ctx.strokeStyle = grid();
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.l, pad.t);
    ctx.lineTo(pad.l, h - pad.b);
    ctx.lineTo(w - pad.r, h - pad.b);
    ctx.stroke();

    // Banda de referencia clínica (rango normal del indicador)
    if (o.bandaDesde != null && o.bandaHasta != null && labels.length > 1) {
      const x0 = pad.l + (o.bandaDesde / n) * innerW;
      const x1 = pad.l + (o.bandaHasta / n) * innerW;
      ctx.fillStyle = tono('--dc-ok-suave','rgba(107,154,122,0.13)');
      ctx.fillRect(x0, pad.t, Math.max(1, x1 - x0), innerH);
    }

    series.forEach((vals, si) => {
      const col = cols[si % cols.length];
      ctx.beginPath();
      ctx.moveTo(pad.l, h - pad.b);
      vals.forEach((v, i) => {
        const x = pad.l + (i / n) * innerW;
        const y = h - pad.b - ((Number(v) || 0) / mx) * innerH;
        ctx.lineTo(x, y);
      });
      ctx.lineTo(pad.l + innerW, h - pad.b);
      ctx.closePath();
      ctx.globalAlpha = 0.22;
      ctx.fillStyle = col;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.beginPath();
      vals.forEach((v, i) => {
        const x = pad.l + (i / n) * innerW;
        const y = h - pad.b - ((Number(v) || 0) / mx) * innerH;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = col;
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    ctx.fillStyle = muted();
    ctx.font = '600 10px Figtree, sans-serif';
    ctx.textAlign = 'center';
    labels.forEach((lab, i) => {
      ctx.fillText(String(lab).slice(0, 9), pad.l + (i / n) * innerW, h - 10);
    });
    ctx.textAlign = 'right';
    ctx.font = '600 10px IBM Plex Mono, monospace';
    ctx.fillText(String(Math.round(mx)), pad.l - 4, pad.t + 8);
  }

  /**
   * Matriz de 100 puntos: cada punto es 1 % de la cohorte.
   * Sustituye al pastel para proporciones: se lee la parte sin estimar
   * ángulos, que es justo lo que un sector circular hace mal.
   */
  function waffle(canvas, labels, values, colors, opts) {
    const o = opts || {};
    if (!canvas) return;
    // La retícula se dimensiona ANTES de crear el lienzo: primero cuántas
    // columnas entran a lo ancho, y con eso cuánto alto hace falta. Fijar
    // 10x10 en una tarjeta ancha y baja dejaba media tarjeta vacía a los lados
    // y, al ensancharla, la mitad inferior en blanco.
    const wCss = Math.max(160, canvas.clientWidth
      || (canvas.parentElement && canvas.parentElement.clientWidth) || 320);
    const anchoLeyenda = Math.min(wCss * 0.38, 150);
    const dispW = Math.max(60, wCss - anchoLeyenda - 16);
    const paso = Math.max(10, Math.min(24, dispW / 20));
    const cols = Math.max(5, Math.min(25, Math.floor(dispW / paso)));
    const filas = Math.ceil(100 / cols);
    const altoLeyenda = labels.length * 22;
    const alto = Math.max(72, filas * paso + 14, altoLeyenda + 10);

    const g = prep(canvas, o.height || alto);
    if (!g) return;
    const { ctx, w, h } = g;
    const total = values.reduce((a, b) => a + (Number(b) || 0), 0) || 1;
    const r = Math.max(2.5, paso * 0.36);
    const x0 = 6;
    const y0 = Math.max(4, (h - paso * filas) / 2);
    const xLeyenda = x0 + paso * cols + 16;

    // Reparto de los 100 puntos respetando el total (el resto al mayor)
    const cuota = values.map((v) => (Number(v) || 0) / total * 100);
    const enteros = cuota.map(Math.floor);
    let faltan = 100 - enteros.reduce((a, b) => a + b, 0);
    const orden = cuota.map((c, i) => [c - Math.floor(c), i]).sort((a, b) => b[0] - a[0]);
    for (let k = 0; k < faltan; k++) enteros[orden[k % orden.length][1]] += 1;

    const plano = [];
    enteros.forEach((n, i) => { for (let k = 0; k < n; k++) plano.push(i); });

    plano.forEach((si, idx) => {
      const cx = x0 + (idx % cols) * paso + paso / 2;
      const cy = y0 + Math.floor(idx / cols) * paso + paso / 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = (colors && colors[si]) || PAL[si % PAL.length];
      ctx.fill();
    });

    // Leyenda centrada verticalmente contra la retícula, no colgada arriba.
    let ly = Math.max(4, (h - altoLeyenda) / 2);
    ctx.textAlign = 'left';
    ctx.font = '600 11px Figtree, sans-serif';
    labels.forEach((lab, i) => {
      ctx.fillStyle = (colors && colors[i]) || PAL[i % PAL.length];
      ctx.beginPath();
      ctx.arc(xLeyenda + 5, ly + 6, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = ink();
      ctx.fillText(`${lab}  ${enteros[i]}%`, xLeyenda + 15, ly + 10);
      ly += 22;
    });
  }

  /**
   * Piruleta horizontal: una línea guía y un punto en el valor.
   * Para comparar categorías sin el peso visual de la barra; el ojo compara
   * posiciones de puntos, que es más preciso que comparar áreas.
   */
  function lollipop(canvas, labels, values, opts) {
    const o = opts || {};
    // Altura segun cuantas categorias haya: con 3 filas, un canvas de 220 px
    // dejaba dos tercios en blanco. La tarjeta se encoge a lo que hace falta.
    const n = labels.length || 1;
    const alto = Math.max(96, Math.min(o.height || 240, 20 + n * 40));
    const g = prep(canvas, alto);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: Math.min(104, w * 0.30), r: 46, t: 10, b: 10 };
    const innerW = w - pad.l - pad.r;
    const paso = (h - pad.t - pad.b) / n;
    const y0 = pad.t;
    const mx = o.max || maxOf(values) || 1;
    const col = o.color || PAL[0];
    const suf = o.suffix || '';

    labels.forEach((lab, i) => {
      const y = y0 + paso * i + paso / 2;
      ctx.strokeStyle = grid();
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + innerW, y);
      ctx.stroke();

      const v = Number(values[i]) || 0;
      const x = pad.l + (v / mx) * innerW;
      ctx.strokeStyle = col;
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();

      ctx.fillStyle = muted();
      ctx.font = '600 10px Figtree, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(String(lab).slice(0, 18), pad.l - 8, y + 3.5);
      ctx.fillStyle = ink();
      ctx.font = '600 10px IBM Plex Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(v.toFixed(1).replace('.', ',') + suf, x + 9, y + 3.5);
    });
  }

  /**
   * Mancuerna: dos puntos unidos por una línea, uno por cohorte.
   * Hecha para contrastar DM+ contra DM-: lo que importa es la brecha, y aquí
   * la brecha es literalmente el segmento entre ambos puntos.
   */
  function dumbbell(canvas, labels, serieA, serieB, opts) {
    const o = opts || {};
    // Mismo criterio que la piruleta, mas la franja de la leyenda.
    const n = labels.length || 1;
    const alto = Math.max(104, Math.min(o.height || 240, 34 + n * 44));
    const g = prep(canvas, alto);
    if (!g) return;
    const { ctx, w, h } = g;
    const pad = { l: Math.min(104, w * 0.28), r: 50, t: 24, b: 10 };
    const innerW = w - pad.l - pad.r;
    const paso = (h - pad.t - pad.b) / n;
    const y0 = pad.t;
    const mx = o.max || maxOf([...serieA, ...serieB]) || 1;
    const colA = o.colorA || ROL.riesgo;
    const colB = o.colorB || ROL.ok;
    const suf = o.suffix || '';

    ctx.textAlign = 'left';
    ctx.font = '600 10px Figtree, sans-serif';
    [[o.labelA || 'DM+', colA, pad.l], [o.labelB || 'DM-', colB, pad.l + 70]].forEach(([t, c, x]) => {
      ctx.fillStyle = c;
      ctx.beginPath();
      ctx.arc(x + 4, 10, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = ink();
      ctx.fillText(t, x + 13, 13.5);
    });

    labels.forEach((lab, i) => {
      const y = y0 + paso * i + paso / 2;
      const a = Number(serieA[i]) || 0;
      const b = Number(serieB[i]) || 0;
      const xa = pad.l + (a / mx) * innerW;
      const xb = pad.l + (b / mx) * innerW;

      ctx.strokeStyle = grid();
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + innerW, y);
      ctx.stroke();

      ctx.strokeStyle = ROL.info;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(xa, y);
      ctx.lineTo(xb, y);
      ctx.stroke();

      [[xb, colB], [xa, colA]].forEach(([x, c]) => {
        ctx.beginPath();
        ctx.arc(x, y, 5.2, 0, Math.PI * 2);
        ctx.fillStyle = c;
        ctx.fill();
      });

      ctx.fillStyle = muted();
      ctx.font = '600 10px Figtree, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(String(lab).slice(0, 18), pad.l - 8, y + 3.5);
      ctx.fillStyle = ink();
      ctx.font = '600 10px IBM Plex Mono, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(Math.abs(a - b).toFixed(1).replace('.', ',') + suf, Math.max(xa, xb) + 9, y + 3.5);
    });
  }

  w.DiabCareGraf = { doughnut, bars, line, scatter, areas, waffle, lollipop, dumbbell, pal: PAL, rol: ROL };
})(window);
