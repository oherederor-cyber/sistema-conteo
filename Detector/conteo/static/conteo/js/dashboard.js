(function () {
  const { apiUrl } = window.CONTEO_CONFIG;
  const $ = (id) => document.getElementById(id);
  const MAX_EVENTOS = 8;

  // Estadísticas de la sesión (desde que se abrió la página).
  let maximo = 0, suma = 0, lecturas = 0;
  let ultimaCantidad = null;

  function registrarActividad(d) {
    maximo = Math.max(maximo, d.cantidad);
    suma += d.cantidad;
    lecturas += 1;
    $("sesion-max").textContent = maximo;
    $("sesion-prom").textContent = (suma / lecturas).toFixed(1);

    // Solo se agrega una fila cuando el número de personas cambia.
    if (d.cantidad === ultimaCantidad) return;
    const anterior = ultimaCantidad;
    ultimaCantidad = d.cantidad;

    const lista = $("lista-actividad");
    if (anterior === null) lista.innerHTML = "";

    let icono = "bi-dot", color = "text-body-secondary";
    if (anterior !== null) {
      icono = d.cantidad > anterior ? "bi-arrow-up-circle-fill" : "bi-arrow-down-circle-fill";
      color = d.cantidad > anterior ? "text-success" : "text-secondary";
    }
    if (d.excedido) color = "text-danger";

    const fila = document.createElement("li");
    fila.className = "list-group-item d-flex justify-content-between align-items-center px-0";
    const personas = d.cantidad === 1 ? "persona" : "personas";
    fila.innerHTML =
      `<span><i class="bi ${icono} ${color}"></i> ${d.cantidad} ${personas}</span>` +
      `<span class="text-body-secondary">${new Date(d.timestamp).toLocaleTimeString()}</span>`;
    lista.prepend(fila);
    while (lista.children.length > MAX_EVENTOS) lista.lastElementChild.remove();
  }

  function actualizar(d) {
    $("cantidad").textContent = d.cantidad;
    $("aforo").textContent = d.aforo;
    $("fps").textContent = d.fps;
    $("detector").textContent = d.detector;
    $("hora").textContent = new Date(d.timestamp).toLocaleTimeString();

    const pct = d.aforo ? Math.min(100, (d.cantidad / d.aforo) * 100) : 0;
    const barra = $("barra-aforo");
    barra.style.width = pct + "%";
    barra.className = "progress-bar " + (d.excedido ? "bg-danger" : pct >= 80 ? "bg-warning" : "bg-success");

    $("tarjeta-conteo").classList.toggle("tarjeta-exceso", d.excedido);
    $("aviso-exceso").classList.toggle("d-none", !d.excedido);

    const estado = $("estado-camara");
    estado.textContent = d.activa ? "En vivo" : (d.error || "Sin señal");
    estado.className = "badge " + (d.activa ? "text-bg-success" : "text-bg-danger");

    registrarActividad(d);
  }

  async function consultar() {
    try {
      const r = await fetch(apiUrl, { cache: "no-store" });
      if (r.ok) actualizar(await r.json());
    } catch (e) {
      $("estado-camara").textContent = "Sin conexión";
      $("estado-camara").className = "badge text-bg-danger";
    }
  }

  consultar();
  setInterval(consultar, 1000);
})();
