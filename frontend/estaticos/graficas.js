/**
 * Gráficas canvas locales (sin CDN) para el módulo de análisis.
 */
(function (w) {
  const PAL = ['#8FB4BE', '#C4A06A', '#6B9A7A', '#C46B6B', '#A98D72', '#8DA79F', '#B3D0D6'];

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

  w.DiabCareGraf = { doughnut, bars, line, pal: PAL };
})(window);
