// generador.js — Módulo generador de datos sintéticos

async function generarDatos() {
  const cantidad = parseInt(document.getElementById('gen-cantidad').value) || 100000;
  const anio     = parseInt(document.getElementById('gen-anio').value) || 2024;
  const btn      = document.getElementById('btn-generar');
  const alerta   = document.getElementById('alerta-generador');
  const progreso = document.getElementById('progreso-generador');
  const barra    = document.getElementById('barra-progreso');
  const texto    = document.getElementById('texto-progreso');

  btn.disabled = true;
  btn.textContent = '⏳ Generando...';
  alerta.innerHTML = '';
  progreso.style.display = 'block';
  barra.style.width = '0%';
  texto.textContent = 'Iniciando generación...';

  try {
    const res = await fetch('/api/generar-sinteticos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cantidad, anio })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error al generar');
    }

    // Leer stream de progreso
    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lineas = decoder.decode(value).split('\n').filter(l => l.trim());
      for (const linea of lineas) {
        try {
          const data = JSON.parse(linea);
          if (data.progreso !== undefined) {
            barra.style.width = data.progreso + '%';
            texto.textContent = data.mensaje || '';
          }
          if (data.listo) {
            alerta.innerHTML = `<div class="alerta-exito">✅ ${data.mensaje}</div>`;
            await verificarPocketBase();
          }
          if (data.error) {
            throw new Error(data.error);
          }
        } catch (e) {
          if (e.message !== 'Unexpected end of JSON input') {
            alerta.innerHTML = `<div class="alerta-error">❌ ${e.message}</div>`;
          }
        }
      }
    }
  } catch (err) {
    alerta.innerHTML = `<div class="alerta-error">❌ ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🧬 Generar y subir a PocketBase';
    setTimeout(() => { progreso.style.display = 'none'; }, 3000);
  }
}

async function verificarPocketBase() {
  const el = document.getElementById('estado-pocketbase');
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    const total = data.diabetes_dataset || 0;
    el.innerHTML = `
      <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:8px;">
        <div><span style="color:var(--texto3);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Registros en PocketBase</span><div style="font-size:28px;font-weight:800;color:var(--violeta3);font-family:'JetBrains Mono',monospace;">${total.toLocaleString('es-EC')}</div></div>
        <div><span style="color:var(--texto3);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Semanas de datos</span><div style="font-size:28px;font-weight:800;color:var(--texto);font-family:'JetBrains Mono',monospace;">${Math.floor(total/100000)}</div></div>
      </div>
    `;
  } catch {
    el.innerHTML = '<span style="color:var(--rojo);">No se pudo conectar con el backend</span>';
  }
}
