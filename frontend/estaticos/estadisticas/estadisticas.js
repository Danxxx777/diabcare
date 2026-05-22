// estadisticas.js — Gráficas estadísticas con Chart.js

let graficasInstancias = {};

function destruirGrafica(id) {
  if (graficasInstancias[id]) {
    graficasInstancias[id].destroy();
    delete graficasInstancias[id];
  }
}

async function cargarEstadisticasGraficas() {
  try {
    const [stats, chartDiabetes, chartGenero, chartBmi, chartGlucosa, chartHba1c, chartCondiciones] = await Promise.all([
      fetch('/api/stats').then(r => r.json()),
      fetch('/api/chart/diabetes').then(r => r.json()),
      fetch('/api/chart/gender').then(r => r.json()),
      fetch('/api/chart/bmi').then(r => r.json()),
      fetch('/api/chart/glucose').then(r => r.json()),
      fetch('/api/chart/hba1c').then(r => r.json()),
      fetch('/api/chart/conditions').then(r => r.json()),
    ]);

    renderDiabetes(chartDiabetes);
    renderGenero(chartGenero);
    renderBmi(chartBmi);
    renderGlucosa(chartGlucosa);
    renderHba1c(chartHba1c);
    renderCondiciones(chartCondiciones);

  } catch (err) {
    console.error('Error cargando estadísticas:', err);
  }
}

const COLORES = {
  violeta: 'rgba(124,58,237,0.8)',
  violetaBorde: 'rgba(124,58,237,1)',
  rosa: 'rgba(236,72,153,0.8)',
  rosaBorde: 'rgba(236,72,153,1)',
  verde: 'rgba(16,185,129,0.8)',
  verdeBorde: 'rgba(16,185,129,1)',
  azul: 'rgba(59,130,246,0.8)',
  azulBorde: 'rgba(59,130,246,1)',
  naranja: 'rgba(245,158,11,0.8)',
  naranjaBorde: 'rgba(245,158,11,1)',
  rojo: 'rgba(239,68,68,0.8)',
  rojoBorde: 'rgba(239,68,68,1)',
};

const OPCIONES_BASE = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { labels: { color: '#a1a1aa', font: { family: 'Outfit', size: 12 } } }
  },
  scales: {
    x: { ticks: { color: '#71717a' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    y: { ticks: { color: '#71717a' }, grid: { color: 'rgba(255,255,255,0.05)' } }
  }
};

function renderDiabetes(data) {
  destruirGrafica('grafica-diabetes');
  const ctx = document.getElementById('grafica-diabetes').getContext('2d');
  graficasInstancias['grafica-diabetes'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Sin Diabetes', 'Con Diabetes'],
      datasets: [{ data: [data.sin_diabetes || 0, data.con_diabetes || 0], backgroundColor: [COLORES.verde, COLORES.rojo], borderColor: [COLORES.verdeBorde, COLORES.rojoBorde], borderWidth: 2 }]
    },
    options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#a1a1aa', font: { family: 'Outfit', size: 12 } } } } }
  });
}

function renderGenero(data) {
  destruirGrafica('grafica-genero');
  const ctx = document.getElementById('grafica-genero').getContext('2d');
  graficasInstancias['grafica-genero'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || [],
      datasets: [{ label: 'Pacientes', data: data.values || [], backgroundColor: COLORES.violeta, borderColor: COLORES.violetaBorde, borderWidth: 1, borderRadius: 6 }]
    },
    options: OPCIONES_BASE
  });
}

function renderBmi(data) {
  destruirGrafica('grafica-bmi');
  const ctx = document.getElementById('grafica-bmi').getContext('2d');
  graficasInstancias['grafica-bmi'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || [],
      datasets: [{ label: 'IMC Promedio', data: data.values || [], backgroundColor: COLORES.azul, borderColor: COLORES.azulBorde, borderWidth: 1, borderRadius: 6 }]
    },
    options: OPCIONES_BASE
  });
}

function renderGlucosa(data) {
  destruirGrafica('grafica-glucosa');
  const ctx = document.getElementById('grafica-glucosa').getContext('2d');
  graficasInstancias['grafica-glucosa'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || [],
      datasets: [{ label: 'Glucosa Promedio', data: data.values || [], backgroundColor: COLORES.naranja, borderColor: COLORES.naranjaBorde, borderWidth: 1, borderRadius: 6 }]
    },
    options: OPCIONES_BASE
  });
}

function renderHba1c(data) {
  destruirGrafica('grafica-hba1c');
  const ctx = document.getElementById('grafica-hba1c').getContext('2d');
  graficasInstancias['grafica-hba1c'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels || [],
      datasets: [{ label: 'Cantidad', data: data.values || [], borderColor: COLORES.rosaBorde, backgroundColor: 'rgba(236,72,153,0.1)', borderWidth: 2, fill: true, tension: 0.4, pointRadius: 3 }]
    },
    options: OPCIONES_BASE
  });
}

function renderCondiciones(data) {
  destruirGrafica('grafica-condiciones');
  const ctx = document.getElementById('grafica-condiciones').getContext('2d');
  graficasInstancias['grafica-condiciones'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || [],
      datasets: [
        { label: 'Hipertensión', data: data.hipertension || [], backgroundColor: COLORES.rojo, borderColor: COLORES.rojoBorde, borderWidth: 1, borderRadius: 6 },
        { label: 'Cardiopatía', data: data.cardiopatia || [], backgroundColor: COLORES.naranja, borderColor: COLORES.naranjaBorde, borderWidth: 1, borderRadius: 6 }
      ]
    },
    options: { ...OPCIONES_BASE, scales: { ...OPCIONES_BASE.scales, x: { ...OPCIONES_BASE.scales.x, stacked: false } } }
  });
}

// Cargar al entrar a la sección
document.addEventListener('DOMContentLoaded', () => {
  const navEstadisticas = document.querySelector('[onclick*="estadisticas"]');
  if (navEstadisticas) {
    navEstadisticas.addEventListener('click', () => {
      setTimeout(cargarEstadisticasGraficas, 100);
    });
  }
});
