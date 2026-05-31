document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }

  initTopNavigation();
  initCustomSelects();
  initPasswordToggles();
  initUploadPreview();
  initScanProgress();
  initPasswordStrength();
  initDataCharts();
  drawCharts();

  window.addEventListener("resize", debounce(drawCharts, 160));
});

function initTopNavigation() {
  const panelToggles = document.querySelectorAll("[data-panel-toggle]");
  const panels = document.querySelectorAll("[data-panel]");
  const searchOpen = document.querySelector("[data-search-open]");
  const searchModal = document.querySelector("[data-search-modal]");
  const searchClose = document.querySelector("[data-search-close]");
  const searchInput = document.getElementById("globalSearchInput");
  let searchReturnTarget = null;

  function closePanels(exceptId = null) {
    panels.forEach((panel) => {
      if (panel.id === exceptId) return;
      panel.hidden = true;
      const toggle = document.querySelector(`[data-panel-toggle="${panel.id}"]`);
      if (toggle) toggle.setAttribute("aria-expanded", "false");
    });
  }

  panelToggles.forEach((toggle) => {
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const panelId = toggle.dataset.panelToggle;
      const panel = document.getElementById(panelId);
      if (!panel) return;
      const willOpen = panel.hidden;
      closePanels(willOpen ? panelId : null);
      panel.hidden = !willOpen;
      toggle.setAttribute("aria-expanded", String(willOpen));
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-topbar-popover]")) {
      closePanels();
    }
  });

  function openSearchModal() {
    if (!searchModal) return;
    closePanels();
    searchReturnTarget = document.activeElement;
    searchModal.hidden = false;
    searchOpen?.setAttribute("aria-expanded", "true");
    window.setTimeout(() => searchInput?.focus(), 0);
  }

  function closeSearchModal() {
    if (!searchModal || searchModal.hidden) return;
    searchModal.hidden = true;
    searchOpen?.setAttribute("aria-expanded", "false");
    if (searchReturnTarget && typeof searchReturnTarget.focus === "function") {
      searchReturnTarget.focus();
    }
  }

  searchOpen?.addEventListener("click", openSearchModal);
  searchClose?.addEventListener("click", closeSearchModal);
  searchModal?.addEventListener("click", (event) => {
    if (event.target === searchModal) {
      closeSearchModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearchModal();
      return;
    }
    if (event.key === "Escape") {
      closePanels();
      closeSearchModal();
    }
  });
}

function initCustomSelects() {
  const selects = document.querySelectorAll("[data-custom-select]");
  if (!selects.length) return;

  function closeSelect(select) {
    const trigger = select._customSelectTrigger || select.querySelector("[data-custom-select-trigger]");
    const menu = select._customSelectMenu || select.querySelector("[data-custom-select-menu]");
    if (!trigger || !menu) return;
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    select.classList.remove("is-open");
  }

  function closeOtherSelects(activeSelect) {
    selects.forEach((select) => {
      if (select !== activeSelect) closeSelect(select);
    });
  }

  function positionMenu(menu, trigger) {
    const rect = trigger.getBoundingClientRect();
    const viewportWidth = document.documentElement.clientWidth;
    const menuWidth = Math.max(rect.width, 14 * 16);
    let left = window.scrollX + rect.left;
    const rightEdge = window.scrollX + viewportWidth - 12;

    if (left + menuWidth > rightEdge) {
      left = Math.max(window.scrollX + 12, rightEdge - menuWidth);
    }

    menu.style.position = "absolute";
    menu.style.left = `${left}px`;
    menu.style.top = `${window.scrollY + rect.bottom + 8}px`;
    menu.style.width = `${Math.min(menuWidth, viewportWidth - 24)}px`;
  }

  selects.forEach((select) => {
    const trigger = select.querySelector("[data-custom-select-trigger]");
    const menu = select.querySelector("[data-custom-select-menu]");
    const input = select.querySelector("[data-custom-select-input]");
    const label = select.querySelector("[data-custom-select-label]");
    const options = Array.from(select.querySelectorAll("[data-value]"));

    if (!trigger || !menu || !input || !label || !options.length) return;
    select._customSelectTrigger = trigger;
    select._customSelectMenu = menu;
    if (menu.parentElement !== document.body) {
      document.body.appendChild(menu);
    }

    function openSelect() {
      closeOtherSelects(select);
      positionMenu(menu, trigger);
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      select.classList.add("is-open");
    }

    function toggleSelect() {
      if (menu.hidden) openSelect();
      else closeSelect(select);
    }

    function selectOption(option) {
      input.value = option.dataset.value || "";
      label.textContent = option.textContent.trim();
      label.dataset.statusValue = input.value;
      options.forEach((item) => {
        const isSelected = item === option;
        item.classList.toggle("is-selected", isSelected);
        item.setAttribute("aria-selected", String(isSelected));
      });
      closeSelect(select);
      trigger.focus();
    }

    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleSelect();
    });

    trigger.addEventListener("keydown", (event) => {
      if (!["ArrowDown", "Enter", " "].includes(event.key)) return;
      event.preventDefault();
      openSelect();
      const current = options.find((option) => option.classList.contains("is-selected")) || options[0];
      current.focus();
    });

    options.forEach((option, index) => {
      option.addEventListener("click", (event) => {
        event.stopPropagation();
        selectOption(option);
      });

      option.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          closeSelect(select);
          trigger.focus();
          return;
        }

        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectOption(option);
          return;
        }

        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          const direction = event.key === "ArrowDown" ? 1 : -1;
          const nextIndex = (index + direction + options.length) % options.length;
          options[nextIndex].focus();
        }
      });
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-custom-select]")) {
      selects.forEach(closeSelect);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      selects.forEach(closeSelect);
    }
  });
}

function initPasswordToggles() {
  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.parentElement.querySelector("input");
      if (!input) return;
      input.type = input.type === "password" ? "text" : "password";
      const icon = input.type === "password" ? "eye" : "eye-off";
      button.innerHTML = `<i data-lucide="${icon}"></i>`;
      if (window.lucide) window.lucide.createIcons();
    });
  });
}

function initUploadPreview() {
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("qrUploadInput");
  const preview = document.getElementById("qrPreview");
  const fallback = document.getElementById("qrPreviewFallback");
  const fileName = document.getElementById("fileName");

  if (!dropzone || !input) return;

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragging");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const files = event.dataTransfer.files;
    if (!files.length) return;
    input.files = files;
    updatePreview(files[0]);
  });

  input.addEventListener("change", () => {
    if (input.files.length) updatePreview(input.files[0]);
  });

  function updatePreview(file) {
    if (fileName) fileName.textContent = file.name;
    if (!preview || !fallback || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      preview.src = event.target.result;
      preview.classList.remove("hidden");
      fallback.classList.add("hidden");
    };
    reader.readAsDataURL(file);
  }
}

function initScanProgress() {
  document.querySelectorAll("[data-scan-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const progress = form.querySelector("[data-scan-progress]");
      const button = form.querySelector("button[type='submit']");
      if (progress) {
        progress.hidden = false;
        const bar = progress.querySelector("span");
        if (bar) bar.style.width = "78%";
      }
      if (button) {
        button.setAttribute("aria-busy", "true");
        button.classList.add("is-loading");
      }
    });
  });
}

function initPasswordStrength() {
  const input = document.getElementById("registerPassword");
  const bar = document.getElementById("strengthBar");
  if (!input || !bar) return;

  input.addEventListener("input", () => {
    const value = input.value;
    let score = 0;
    if (value.length >= 8) score += 25;
    if (value.length >= 12) score += 20;
    if (/[A-Z]/.test(value)) score += 15;
    if (/[0-9]/.test(value)) score += 15;
    if (/[^A-Za-z0-9]/.test(value)) score += 25;
    bar.style.width = `${Math.min(score, 100)}%`;
  });
}

function initDataCharts() {
  if (!window.Chart) return;

  window.Chart.defaults.color = "rgba(231,226,242,.78)";
  window.Chart.defaults.borderColor = "rgba(255,255,255,.08)";
  window.Chart.defaults.font.family = "Inter, ui-sans-serif, system-ui, Segoe UI, Arial, sans-serif";

  const dashboard = readJsonScript("dashboard-chart-data");
  if (dashboard) {
    renderDoughnutChart("dashboardRiskChart", dashboard.risk_distribution);
    renderLineChartJs("dashboardTrendChart", dashboard.trend.labels, [
      {
        label: "Total scans",
        data: dashboard.trend.total,
        borderColor: "#b45cff",
        backgroundColor: "rgba(180,92,255,.18)",
      },
    ]);
    renderDoughnutChart("dashboardReportChart", dashboard.reports);
  }

  const analytics = readJsonScript("security-analytics-data");
  if (analytics) {
    renderDoughnutChart("analyticsRiskChart", analytics.risk_distribution);
    renderLineChartJs("analyticsTrendChart", analytics.trend.labels, [
      {
        label: "Total scans",
        data: analytics.trend.total,
        borderColor: "#b45cff",
        backgroundColor: "rgba(180,92,255,.14)",
      },
      {
        label: "Warnings",
        data: analytics.trend.warning,
        borderColor: "#f7c948",
        backgroundColor: "rgba(247,201,72,.1)",
      },
      {
        label: "Malicious",
        data: analytics.trend.malicious,
        borderColor: "#ff2d68",
        backgroundColor: "rgba(255,45,104,.12)",
      },
    ]);
    renderBarChart("analyticsDomainsChart", analytics.top_domains);
    renderDoughnutChart("analyticsReportChart", analytics.reports);
  }
}

function readJsonScript(id) {
  const element = document.getElementById(id);
  if (!element) return null;
  try {
    return JSON.parse(element.textContent);
  } catch (error) {
    return null;
  }
}

function getCanvas(id) {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return null;
  return canvas;
}

function renderDoughnutChart(id, dataset) {
  const canvas = getCanvas(id);
  if (!canvas || !dataset) return;
  const values = dataset.values || [];
  new window.Chart(canvas, {
    type: "doughnut",
    data: {
      labels: dataset.labels || [],
      datasets: [
        {
          data: values,
          backgroundColor: ["#36d98a", "#f7c948", "#ff2d68", "#8a8794"],
          borderColor: "rgba(255,255,255,.12)",
          borderWidth: 1,
        },
      ],
    },
    options: chartOptions({ cutout: "68%" }),
  });
}

function renderLineChartJs(id, labels, datasets) {
  const canvas = getCanvas(id);
  if (!canvas) return;
  new window.Chart(canvas, {
    type: "line",
    data: {
      labels: labels || [],
      datasets: (datasets || []).map((dataset) => ({
        ...dataset,
        fill: true,
        tension: 0.38,
        pointRadius: 2.5,
        pointHoverRadius: 4,
        borderWidth: 2,
      })),
    },
    options: chartOptions({
      scales: {
        x: gridScale(),
        y: { ...gridScale(), beginAtZero: true, ticks: { precision: 0 } },
      },
    }),
  });
}

function renderBarChart(id, dataset) {
  const canvas = getCanvas(id);
  if (!canvas || !dataset) return;
  new window.Chart(canvas, {
    type: "bar",
    data: {
      labels: dataset.labels || [],
      datasets: [
        {
          label: "Risky scans",
          data: dataset.values || [],
          backgroundColor: "rgba(255,45,104,.45)",
          borderColor: "#ff2d68",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: chartOptions({
      scales: {
        x: gridScale(),
        y: { ...gridScale(), beginAtZero: true, ticks: { precision: 0 } },
      },
    }),
  });
}

function chartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          boxWidth: 10,
          boxHeight: 10,
        },
      },
      tooltip: {
        backgroundColor: "rgba(10,9,14,.94)",
        borderColor: "rgba(168,85,247,.35)",
        borderWidth: 1,
      },
    },
    ...extra,
  };
}

function gridScale() {
  return {
    grid: { color: "rgba(255,255,255,.08)" },
    ticks: { color: "rgba(231,226,242,.72)" },
  };
}

function drawCharts() {
  document.querySelectorAll('canvas[data-chart="line"]').forEach((canvas) => {
    const values = (canvas.dataset.values || "0")
      .split(",")
      .map((value) => Number.parseFloat(value.trim()))
      .filter((value) => Number.isFinite(value));
    drawLineChart(canvas, values.length ? values : [0, 1, 0]);
  });
}

function drawLineChart(canvas, values) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const width = rect.width;
  const height = rect.height;
  const pad = 18;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const spread = Math.max(max - min, 1);

  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(255,255,255,.08)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i += 1) {
    const y = pad + ((height - pad * 2) / 3) * i;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }

  const points = values.map((value, index) => {
    const x = pad + ((width - pad * 2) / Math.max(values.length - 1, 1)) * index;
    const y = height - pad - ((value - min) / spread) * (height - pad * 2);
    return { x, y };
  });

  const fill = ctx.createLinearGradient(0, pad, 0, height - pad);
  fill.addColorStop(0, "rgba(255,45,104,.34)");
  fill.addColorStop(1, "rgba(139,92,246,0)");

  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.lineTo(points[points.length - 1].x, height - pad);
  ctx.lineTo(points[0].x, height - pad);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();

  const stroke = ctx.createLinearGradient(pad, 0, width - pad, 0);
  stroke.addColorStop(0, "#8b5cf6");
  stroke.addColorStop(1, "#ff2d68");
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(255,45,104,.55)";
  ctx.shadowBlur = 12;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();
  ctx.shadowBlur = 0;

  points.forEach((point) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 3.4, 0, Math.PI * 2);
    ctx.fillStyle = "#f7c9ff";
    ctx.fill();
  });
}

function debounce(fn, delay) {
  let timeout;
  return (...args) => {
    window.clearTimeout(timeout);
    timeout = window.setTimeout(() => fn(...args), delay);
  };
}
