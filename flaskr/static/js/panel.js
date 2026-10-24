(() => {
  "use strict";

  const state = { reservations: [], courts: [] };
  const elements = {
    rows: document.querySelector("#reservation-rows"),
    search: document.querySelector("#search-input"),
    status: document.querySelector("#status-filter"),
    date: document.querySelector("#date-filter"),
    empty: document.querySelector("#empty-state"),
    visibleCount: document.querySelector("#visible-count"),
    footerCount: document.querySelector("#footer-count"),
    loadError: document.querySelector("#load-error"),
    loadErrorMessage: document.querySelector("#load-error-message"),
    dialog: document.querySelector("#booking-dialog"),
    form: document.querySelector("#booking-form"),
    formError: document.querySelector("#form-error"),
    courtSelect: document.querySelector("#court-select"),
    clientSearch: document.querySelector("#client-search"),
    clientId: document.querySelector("#client-id"),
    clientResults: document.querySelector("#client-results"),
    selectedClient: document.querySelector("#selected-client"),
    toastRegion: document.querySelector("#toast-region"),
  };

  const statusLabels = {
    PENDIENTE: "Pendiente",
    CONFIRMADA: "Confirmada",
    CANCELADA: "Cancelada",
    COMPLETADA: "Completada",
  };
  const statusClasses = {
    PENDIENTE: "badge-pending",
    CONFIRMADA: "badge-confirmed",
    CANCELADA: "badge-cancelled",
    COMPLETADA: "badge-completed",
  };
  const sportIcons = { futbol: "⚽", tenis: "◉", baloncesto: "◉", padel: "⌁" };
  const currency = new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  });

  async function request(url, options = {}) {
    const response = await fetch(url, {
      headers: { Accept: "application/json", ...options.headers },
      ...options,
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("El servidor devolvió una respuesta que no es JSON.");
    }
    if (!response.ok) {
      throw new Error(data.error || `La solicitud falló (${response.status}).`);
    }
    return data;
  }

  function formatDate(value, options = { day: "2-digit", month: "short", year: "numeric" }) {
    return new Intl.DateTimeFormat("es-CO", options).format(new Date(value));
  }

  function formatTime(value) {
    return new Intl.DateTimeFormat("es-CO", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(value));
  }

  function makeCell(className, content, secondary) {
    const cell = document.createElement("td");
    if (secondary === undefined) {
      cell.textContent = content;
      cell.className = className || "";
      return cell;
    }
    const primary = document.createElement("span");
    primary.className = className;
    primary.textContent = content;
    const sub = document.createElement("span");
    sub.className = "sub-cell";
    sub.textContent = secondary;
    cell.append(primary, sub);
    return cell;
  }

  function actionButton(label, action, reservationId) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "action-button";
    button.textContent = label;
    button.dataset.action = action;
    button.dataset.id = reservationId;
    return button;
  }

  function createReservationRow(reservation) {
    const row = document.createElement("tr");
    const idCell = document.createElement("td");
    const id = document.createElement("span");
    id.className = "booking-id";
    id.textContent = String(reservation.id);
    idCell.append(id);
    row.append(idCell);

    const court = state.courts.find((item) => item.id === reservation.cancha_id);
    row.append(makeCell("main-cell", court ? court.nombre : `Cancha #${reservation.cancha_id}`, court ? court.deporte : "Deporte"));
    row.append(makeCell("main-cell", `Cliente #${reservation.cliente_id}`, "Reserva registrada"));

    const dateCell = document.createElement("td");
    const date = document.createElement("span");
    date.className = "date-cell";
    date.textContent = formatDate(reservation.fecha_inicio);
    const time = document.createElement("span");
    time.className = "time-cell";
    time.textContent = `${formatTime(reservation.fecha_inicio)} – ${formatTime(reservation.fecha_fin)}`;
    dateCell.append(date, time);
    row.append(dateCell);

    const amount = document.createElement("span");
    amount.className = "amount-cell";
    amount.textContent = currency.format(reservation.total);
    const amountCell = document.createElement("td");
    amountCell.append(amount);
    row.append(amountCell);

    const badgeCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge ${statusClasses[reservation.estado] || ""}`;
    badge.textContent = statusLabels[reservation.estado] || reservation.estado;
    badgeCell.append(badge);
    row.append(badgeCell);

    const actionsCell = document.createElement("td");
    const actions = document.createElement("div");
    actions.className = "row-actions";
    if (reservation.estado === "PENDIENTE") {
      actions.append(actionButton("Confirmar", "confirmar", reservation.id));
      actions.append(actionButton("Cancelar", "cancelar", reservation.id));
    } else if (reservation.estado === "CONFIRMADA") {
      actions.append(actionButton("Completar", "completar", reservation.id));
      actions.append(actionButton("Cancelar", "cancelar", reservation.id));
    }
    actionsCell.append(actions);
    row.append(actionsCell);
    return row;
  }

  function filteredReservations() {
    const term = elements.search.value.trim().toLocaleLowerCase("es");
    const selectedStatus = elements.status.value;
    const selectedDate = elements.date.value;
    return state.reservations.filter((reservation) => {
      if (selectedStatus && reservation.estado !== selectedStatus) return false;
      if (selectedDate && reservation.fecha_inicio.slice(0, 10) !== selectedDate) return false;
      const court = state.courts.find((item) => item.id === reservation.cancha_id);
      const searchable = [
        String(reservation.id),
        String(reservation.cliente_id),
        court ? court.nombre : "",
        statusLabels[reservation.estado] || reservation.estado,
      ].join(" ").toLocaleLowerCase("es");
      return !term || searchable.includes(term);
    });
  }

  function renderReservations() {
    const reservations = filteredReservations();
    elements.rows.replaceChildren(...reservations.map(createReservationRow));
    elements.empty.hidden = reservations.length > 0;
    elements.visibleCount.textContent = String(reservations.length);
    elements.footerCount.textContent = String(reservations.length);
  }

  function renderStats() {
    document.querySelector("#stat-total").textContent = String(state.reservations.length);
    document.querySelector("#stat-pending").textContent = String(state.reservations.filter((r) => r.estado === "PENDIENTE").length);
    document.querySelector("#stat-confirmed").textContent = String(state.reservations.filter((r) => r.estado === "CONFIRMADA").length);
    document.querySelector("#stat-courts").textContent = String(state.courts.length);
  }

  function renderCourts() {
    const grid = document.querySelector("#courts-grid");
    grid.replaceChildren();
    document.querySelector("#courts-caption").textContent = `${state.courts.length} espacios disponibles`;
    state.courts.forEach((court) => {
      const card = document.createElement("article");
      card.className = "court-card";
      const top = document.createElement("div");
      top.className = "court-card-top";
      const icon = document.createElement("span");
      icon.className = "sport-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = sportIcons[court.deporte] || "⌁";
      const active = document.createElement("span");
      active.className = "active-label";
      active.textContent = "Activa";
      top.append(icon, active);
      const name = document.createElement("strong");
      name.textContent = court.nombre;
      const price = document.createElement("small");
      price.textContent = `${currency.format(court.precio_hora)} / hora`;
      card.append(top, name, price);
      grid.append(card);
    });
    if (state.courts.length === 0) {
      const empty = document.createElement("div");
      empty.className = "court-loading";
      empty.textContent = "No hay canchas activas para mostrar.";
      grid.append(empty);
    }
  }

  function renderCourtOptions() {
    elements.courtSelect.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Selecciona una cancha";
    elements.courtSelect.append(placeholder);
    state.courts.forEach((court) => {
      const option = document.createElement("option");
      option.value = String(court.id);
      option.textContent = `${court.nombre} · ${currency.format(court.precio_hora)}/h`;
      elements.courtSelect.append(option);
    });
  }

  async function loadDashboard() {
    elements.loadError.hidden = true;
    elements.rows.innerHTML = '<tr><td class="loading-cell" colspan="7"><span class="spinner"></span> Cargando reservas…</td></tr>';
    try {
      const [reservations, courts] = await Promise.all([
        request("/api/reservas"),
        request("/api/canchas"),
      ]);
      state.reservations = reservations;
      state.courts = courts;
      renderStats();
      renderReservations();
      renderCourts();
      renderCourtOptions();
    } catch (error) {
      elements.rows.replaceChildren();
      elements.loadErrorMessage.textContent = error.message;
      elements.loadError.hidden = false;
      elements.empty.hidden = true;
      toast(`No se pudo cargar el panel: ${error.message}`, true);
    }
  }

  function toast(message, isError = false) {
    const item = document.createElement("div");
    item.className = `toast${isError ? " error" : ""}`;
    item.textContent = message;
    elements.toastRegion.append(item);
    window.setTimeout(() => item.remove(), 4200);
  }

  function openDialog() {
    elements.form.reset();
    elements.clientId.value = "";
    elements.clientResults.hidden = true;
    elements.selectedClient.textContent = "Escribe al menos 2 caracteres para buscar.";
    elements.selectedClient.classList.remove("selected");
    elements.formError.hidden = true;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dateString = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    document.querySelector("#booking-date").value = dateString;
    document.querySelector("#booking-date").min = new Date().toISOString().slice(0, 10);
    elements.dialog.showModal();
  }

  let searchTimer;
  async function searchClients() {
    const query = elements.clientSearch.value.trim();
    elements.clientId.value = "";
    elements.selectedClient.textContent = "Escribe al menos 2 caracteres para buscar.";
    elements.selectedClient.classList.remove("selected");
    if (query.length < 2) {
      elements.clientResults.hidden = true;
      return;
    }
    elements.clientResults.replaceChildren();
    const loading = document.createElement("div");
    loading.className = "client-empty";
    loading.textContent = "Buscando clientes…";
    elements.clientResults.append(loading);
    elements.clientResults.hidden = false;
    try {
      const clients = await request(`/api/clientes?q=${encodeURIComponent(query)}`);
      elements.clientResults.replaceChildren();
      if (!clients.length) {
        const noResults = document.createElement("div");
        noResults.className = "client-empty";
        noResults.textContent = "No encontramos clientes con esa búsqueda.";
        elements.clientResults.append(noResults);
      }
      clients.forEach((client) => {
        const option = document.createElement("button");
        option.type = "button";
        option.className = "client-option";
        option.setAttribute("role", "option");
        option.append(document.createTextNode(client.nombre));
        const detail = document.createElement("small");
        detail.textContent = `Documento: ${client.documento} · Cliente #${client.id}`;
        option.append(detail);
        option.addEventListener("click", () => {
          elements.clientSearch.value = client.nombre;
          elements.clientId.value = String(client.id);
          elements.selectedClient.textContent = `Cliente #${client.id} seleccionado`;
          elements.selectedClient.classList.add("selected");
          elements.clientResults.hidden = true;
        });
        elements.clientResults.append(option);
      });
    } catch (error) {
      elements.clientResults.replaceChildren();
      const failure = document.createElement("div");
      failure.className = "client-empty";
      failure.textContent = `No se pudo buscar: ${error.message}`;
      elements.clientResults.append(failure);
    }
  }

  async function updateStatus(button) {
    button.disabled = true;
    try {
      await request(`/api/reservas/${button.dataset.id}/${button.dataset.action}`, { method: "PATCH" });
      toast(`Reserva #${button.dataset.id} actualizada correctamente.`);
      await loadDashboard();
    } catch (error) {
      toast(`No se pudo actualizar la reserva: ${error.message}`, true);
      button.disabled = false;
    }
  }

  document.querySelectorAll("#new-booking-button, #new-booking-button-secondary, #empty-create-button")
    .forEach((button) => button.addEventListener("click", openDialog));
  document.querySelector("#close-dialog").addEventListener("click", () => elements.dialog.close());
  document.querySelector("#cancel-dialog").addEventListener("click", () => elements.dialog.close());
  document.querySelector("#refresh-button").addEventListener("click", loadDashboard);
  document.querySelector("#retry-button").addEventListener("click", loadDashboard);
  elements.search.addEventListener("input", renderReservations);
  elements.status.addEventListener("change", renderReservations);
  elements.date.addEventListener("change", renderReservations);
  elements.rows.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (button) updateStatus(button);
  });
  elements.clientSearch.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(searchClients, 250);
  });
  elements.clientSearch.addEventListener("focus", () => {
    if (elements.clientSearch.value.trim().length >= 2 && !elements.clientId.value) searchClients();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".client-field")) elements.clientResults.hidden = true;
  });
  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    elements.formError.hidden = true;
    if (!elements.clientId.value) {
      elements.formError.textContent = "Selecciona un cliente de los resultados de búsqueda.";
      elements.formError.hidden = false;
      return;
    }
    const date = document.querySelector("#booking-date").value;
    const start = document.querySelector("#booking-start").value;
    const end = document.querySelector("#booking-end").value;
    const button = document.querySelector("#submit-booking");
    button.disabled = true;
    button.textContent = "Guardando…";
    try {
      const reservation = await request("/api/reservas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cancha_id: Number(elements.courtSelect.value),
          cliente_id: Number(elements.clientId.value),
          fecha_inicio: `${date}T${start}:00`,
          fecha_fin: `${date}T${end}:00`,
        }),
      });
      elements.dialog.close();
      toast(`Reserva #${reservation.id} creada. Total: ${currency.format(reservation.total)}.`);
      await loadDashboard();
    } catch (error) {
      elements.formError.textContent = error.message;
      elements.formError.hidden = false;
    } finally {
      button.disabled = false;
      button.innerHTML = 'Guardar reserva <span aria-hidden="true">→</span>';
    }
  });

  document.querySelector("#current-year").textContent = String(new Date().getFullYear());
  loadDashboard();
})();
