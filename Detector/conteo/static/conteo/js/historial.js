(function () {
  const { apiUrl } = window.CONTEO_CONFIG;
  const $ = (id) => document.getElementById(id);

  const grafica = new Chart($("grafica-historial"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "Personas", data: [], tension: 0.25, fill: true, pointRadius: 1, stepped: false },
        { label: "Aforo máximo", data: [], borderDash: [6, 4], pointRadius: 0, borderColor: "#dc3545" },
      ],
    },
    options: {
      animation: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  async function cargar(horas) {
    const r = await fetch(`${apiUrl}?horas=${horas}`, { cache: "no-store" });
    if (!r.ok) return;
    const d = await r.json();
    const etiquetas = d.puntos.map((p) => {
      const f = new Date(p.t);
      return horas > 24 ? f.toLocaleString() : f.toLocaleTimeString();
    });
    grafica.data.labels = etiquetas;
    grafica.data.datasets[0].data = d.puntos.map((p) => p.y);
    grafica.data.datasets[1].data = d.puntos.map(() => d.aforo);
    grafica.update();

    $("r-maximo").textContent = d.resumen.maximo;
    $("r-promedio").textContent = d.resumen.promedio;
    $("r-registros").textContent = d.resumen.registros;
    $("r-alertas").textContent = d.resumen.alertas;
  }

  document.querySelectorAll("#filtro-horas button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filtro-horas button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      cargar(Number(btn.dataset.horas));
    });
  });

  cargar(1);
})();
