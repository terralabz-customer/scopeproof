"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const ui = {
    form: byId("scope-form"), brief: byId("brief"), change: byId("change-request"),
    changeDetails: byId("change-details"), runButton: byId("run-button"),
    runButtonText: byId("run-button-text"), clear: byId("clear-brief"),
    error: byId("form-error"), empty: byId("empty-state"), run: byId("run-panel"),
    runStage: byId("run-stage"), events: byId("run-events"), runError: byId("run-error"),
    result: byId("result-card"), export: byId("export-pack"),
  };
  let running = false;
  let lastResult = null;
  let lastRunId = null;
  let lastBrief = null;
  let pollTimer = null;
  let toastTimer = null;
  let currentRequest = 0;
  let healthRequest = 0;
  let replyText = "";

  // All client and model content is inserted as text, never interpreted as HTML.
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = asText(text);
    return element;
  }

  function asText(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
    if (Array.isArray(value)) return value.map(asText).filter(Boolean).join("\n");
    if (typeof value === "object") {
      if (value.quote || value.text) {
        const source = asText(value.source || value.segment_id);
        return `${source ? `${source}: ` : ""}${asText(value.quote || value.text)}`;
      }
      return Object.entries(value).map(([key, item]) => `${key}: ${asText(item)}`).join("\n");
    }
    return "";
  }

  function list(value) {
    return Array.isArray(value) ? value : [];
  }

  function money(value, currency) {
    if (value === null || value === undefined || value === "") return "Unpriced";
    const amount = Number(value);
    if (!Number.isFinite(amount)) return "Unpriced";
    const unit = asText(currency);
    if (!/^[A-Z]{3}$/.test(unit)) return `${amount.toLocaleString("en-US", { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ""}`;
    try {
      return new Intl.NumberFormat("en-US", { style: "currency", currency: unit, currencyDisplay: "code", minimumFractionDigits: Number.isInteger(amount) ? 0 : 2, maximumFractionDigits: 2 }).format(amount);
    } catch (_) {
      return `${unit} ${amount.toFixed(2)}`;
    }
  }

  function errorText(detail, fallback) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => asText(item.msg || item)).join(" ");
    return fallback;
  }

  async function request(path, options = {}) {
    let response;
    try {
      response = await fetch(path, { cache: "no-store", ...options });
    } catch (_) {
      throw new Error("The local backend could not be reached. Check that ScopeProof is running, then try again.");
    }
    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new Error("The backend returned an unreadable response. No new draft has been displayed.");
    }
    if (!response.ok) {
      const error = new Error(errorText(data.detail || data.error, `The request failed (${response.status}). Please try again.`));
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function loadHealth() {
    const version = ++healthRequest;
    byId("refresh-health").disabled = true;
    try {
      const data = await request("/api/health");
      if (version !== healthRequest) return;
      byId("health-label").textContent = data.ready ? "Local model ready" : "Model not ready";
      byId("health-dot").className = `status-dot ${data.ready ? "ready" : "unavailable"}`;
      byId("health-detail").textContent = asText(data.detail) || (data.ready ? "The configured model is available." : "The model is not ready to accept a run.");
      const metadata = byId("model-metadata");
      metadata.replaceChildren();
      for (const [label, value] of [["Provider", data.provider], ["Model", data.model]]) {
        if (value) metadata.append(node("dt", "", label), node("dd", "", value));
      }
    } catch (error) {
      if (version !== healthRequest) return;
      byId("health-label").textContent = "Backend unavailable";
      byId("health-dot").className = "status-dot unavailable";
      byId("health-detail").textContent = error.message;
      byId("model-metadata").replaceChildren();
    } finally {
      if (version === healthRequest) byId("refresh-health").disabled = false;
    }
  }

  function updateCount() {
    byId("brief-count").textContent = `${ui.brief.value.length.toLocaleString("en-US")} / 12,000`;
    ui.error.hidden = true;
  }

  async function loadCatalog() {
    const container = byId("catalog-list");
    try {
      const data = await request("/api/catalog");
      const services = list(data.services);
      byId("catalog-count").textContent = String(services.length);
      container.replaceChildren();
      for (const service of services) {
        const item = node("article", "catalog-item");
        item.append(node("h4", "", service.name || service.title || "Unnamed service"));
        item.append(node("span", "catalog-price", money(service.base_price ?? service.price, service.currency)));
        if (service.description) item.append(node("p", "", service.description));
        container.append(item);
      }
      if (!services.length) container.append(node("p", "empty-list-note", "No services are available in this catalog."));
    } catch (error) {
      byId("catalog-count").textContent = "—";
      container.replaceChildren(node("p", "loading-note", `Catalog unavailable. ${error.message}`));
    }
  }

  async function loadExamples() {
    const container = byId("sample-list");
    try {
      const data = await request("/api/examples");
      const examples = list(data.examples);
      container.replaceChildren();
      examples.forEach((example, index) => {
        const button = node("button", "sample-card");
        button.type = "button";
        button.setAttribute("aria-label", `Use synthetic sample: ${asText(example.title)}`);
        const number = node("span", "sample-number", String(index + 1).padStart(2, "0"));
        number.setAttribute("aria-hidden", "true");
        const copy = node("span", "sample-copy");
        copy.append(node("span", "sample-title", example.title));
        copy.append(node("span", "sample-description", example.change_request || example.brief));
        const arrow = node("span", "sample-arrow", "↗");
        arrow.setAttribute("aria-hidden", "true");
        button.append(number, copy, arrow);
        button.addEventListener("click", () => {
          if (running) return;
          ui.brief.value = asText(example.brief).slice(0, 12000);
          ui.change.value = asText(example.change_request).slice(0, 4000);
          ui.changeDetails.open = Boolean(ui.change.value);
          updateCount();
          ui.brief.focus({ preventScroll: true });
          if (window.matchMedia("(max-width: 710px)").matches) ui.form.scrollIntoView({ behavior: "smooth", block: "start" });
          toast("Sample loaded. Review the brief, then find the scope.");
        });
        container.append(button);
      });
      if (!examples.length) container.append(node("p", "empty-list-note", "No sample briefs are available. You can paste your own request."));
    } catch (_) {
      container.replaceChildren(node("p", "loading-note", "Samples could not be loaded. Paste your own brief, or refresh when the local backend is available."));
    }
  }

  function toast(message) {
    clearTimeout(toastTimer);
    const element = byId("toast");
    element.textContent = message;
    element.hidden = false;
    toastTimer = setTimeout(() => { element.hidden = true; }, 3600);
  }

  function setBusy(busy) {
    running = busy;
    ui.runButton.disabled = busy;
    ui.clear.disabled = busy;
    ui.brief.readOnly = busy;
    ui.change.readOnly = busy;
    ui.runButton.classList.toggle("is-running", busy);
    ui.runButtonText.textContent = busy ? "Finding the scope…" : (lastResult ? "Review the scope again" : "Find the scope");
    ui.form.setAttribute("aria-busy", String(busy));
    document.querySelectorAll(".sample-card").forEach((button) => { button.disabled = busy; });
    if (busy && lastResult) ui.result.classList.add("stale-result");
    if (!busy) ui.result.classList.remove("stale-result");
  }

  function renderEvents(events) {
    const fragment = document.createDocumentFragment();
    list(events).forEach((event, index) => {
      const raw = asText(event.status).toLowerCase();
      const state = ["complete", "completed", "success", "done"].includes(raw) ? "complete" : ["failed", "error"].includes(raw) ? "failed" : ["running", "started", "in_progress"].includes(raw) ? "running" : raw === "warning" ? "warning" : "pending";
      const item = node("li", `run-event ${state}`);
      const marker = node("span", "event-marker", state === "complete" ? "✓" : ["failed", "warning"].includes(state) ? "!" : state === "running" ? "" : String(index + 1));
      marker.setAttribute("aria-hidden", "true");
      const content = node("div", "event-content");
      const label = node("p", "event-label", event.label || event.step || "Run event");
      const status = node("span", "sr-only", ` (${state})`);
      label.append(status);
      content.append(label);
      if (event.detail) content.append(node("p", "event-detail", event.detail));
      item.append(marker, content);
      fragment.append(item);
    });
    ui.events.replaceChildren(fragment);
  }

  function renderRun(run) {
    const state = asText(run.status);
    byId("run-state-badge").textContent = ({ queued: "Queued", running: "In progress", complete: "Complete", failed: "Stopped" })[state] || "Checking";
    byId("run-state-badge").className = `run-state-badge ${state === "complete" ? "complete" : state === "failed" ? "failed" : ""}`;
    ui.runStage.textContent = asText(run.stage) || (state === "queued" ? "The backend has queued this run." : "Waiting for an update from the backend.");
    renderEvents(run.events);
    ui.run.classList.toggle("is-complete", state === "complete");
    ui.run.classList.toggle("is-failed", state === "failed");
    byId("run-heading").textContent = state === "complete" ? "The scope is ready to review." : state === "failed" ? "This run needs another try." : "Making the brief clearer.";
    if (state === "failed") {
      ui.runError.textContent = asText(run.error) || "The run stopped before it produced a result. Check the model connection and try again.";
      ui.runError.hidden = false;
    }
  }

  function evidence(value) {
    const text = asText(value).trim();
    if (!text) return null;
    const details = node("details", "evidence");
    details.append(node("summary", "", "See source evidence"));
    details.append(node("blockquote", "evidence-content", text));
    return details;
  }

  function addEvidence(parent, value) {
    const element = evidence(value);
    if (element) parent.append(element);
  }

  function renderScope(items) {
    const container = byId("scope-list");
    container.replaceChildren();
    byId("scope-count").textContent = String(items.length);
    items.forEach((item) => {
      const state = ["included", "clarify", "excluded"].includes(item.status) ? item.status : "clarify";
      const row = node("li", `scope-item ${state}`);
      const symbol = node("span", "scope-symbol", ({ included: "✓", clarify: "?", excluded: "−" })[state]);
      symbol.setAttribute("aria-hidden", "true");
      const heading = node("div", "scope-item-heading");
      heading.append(node("p", "scope-text", item.text), node("span", "scope-state", state === "clarify" ? "Needs clarity" : state === "excluded" ? "Outside scope" : "Included"));
      row.append(symbol, heading);
      addEvidence(row, item.evidence);
      container.append(row);
    });
    if (!items.length) container.append(node("li", "empty-list-note", "No scope items were supplied. Clarify the requested work before committing."));
  }

  function renderQuestions(items) {
    const container = byId("questions-list");
    container.replaceChildren();
    byId("question-count").textContent = String(items.length);
    for (const item of items) {
      const card = node("div", "question-item");
      card.append(node("h5", "", item.question));
      if (item.reason) card.append(node("p", "", item.reason));
      addEvidence(card, item.evidence);
      container.append(card);
    }
    if (!items.length) container.append(node("p", "empty-list-note", "No questions were returned. Still review the original brief for gaps."));
  }

  function renderRisks(items) {
    byId("risks-section").hidden = !items.length;
    const container = byId("risks-list");
    container.replaceChildren();
    byId("risk-count").textContent = String(items.length);
    for (const item of items) {
      const severity = asText(item.severity).toLowerCase();
      const card = node("div", `risk-item ${["high", "critical"].includes(severity) ? "high" : ""}`);
      const heading = node("div", "risk-title-line");
      heading.append(node("h5", "", item.title || "Review needed"), node("span", "severity-badge", severity || "Review"));
      card.append(heading);
      if (item.detail) card.append(node("p", "", item.detail));
      addEvidence(card, item.evidence);
      container.append(card);
    }
  }

  function renderComparison(previous, current, sameBrief) {
    const container = byId("comparison");
    container.replaceChildren();
    container.hidden = !previous || !sameBrief;
    if (!previous || !sameBrief) return;
    container.append(node("h4", "", "Compared with your previous draft"));
    const oldQuote = previous.quote || {};
    const newQuote = current.quote || {};
    container.append(node("p", "", `${money(oldQuote.total, oldQuote.currency || previous.currency)} → ${money(newQuote.total, newQuote.currency || current.currency)} · illustrative estimates`));
    const oldItems = list(previous.scope_items);
    const newItems = list(current.scope_items);
    const normalize = (value) => asText(value).trim().toLowerCase();
    const notes = [];
    if (previous.service_id !== current.service_id) notes.push(`Catalog match changed from ${asText(previous.service_name)} to ${asText(current.service_name)}.`);
    for (const item of newItems) {
      const oldItem = oldItems.find((old) => normalize(old.text) === normalize(item.text));
      if (!oldItem) notes.push(`Added for review: ${asText(item.text)}`);
      else if (oldItem.status !== item.status) notes.push(`Classification changed from ${asText(oldItem.status)} to ${asText(item.status)}: ${asText(item.text)}`);
    }
    for (const item of oldItems) {
      if (!newItems.some((currentItem) => normalize(currentItem.text) === normalize(item.text))) notes.push(`No longer listed: ${asText(item.text)}`);
    }
    if (notes.length) {
      const changes = node("ul", "");
      notes.slice(0, 8).forEach((note) => changes.append(node("li", "", note)));
      if (notes.length > 8) changes.append(node("li", "", `${notes.length - 8} more changes. Review the full scope below.`));
      container.append(changes);
    } else container.append(node("p", "", "The listed scope and its classifications are unchanged."));
    container.append(node("p", "", "This comparison describes two drafts, not accepted changes to an agreement."));
  }

  function renderAudit(result) {
    const audit = result.audit && typeof result.audit === "object" ? result.audit : {};
    const metrics = result.metrics && typeof result.metrics === "object" ? result.metrics : {};
    const metadata = byId("audit-metadata");
    const trace = byId("audit-trace");
    metadata.replaceChildren();
    trace.replaceChildren();
    byId("audit-details").open = false;
    function metric(label, value, className = "") {
      const row = node("div", `audit-metric ${className}`);
      row.append(node("dt", "", label), node("dd", "", value));
      metadata.append(row);
    }
    function nonNegative(value) {
      return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
    }
    if (audit.model) metric("Model", asText(audit.model), "audit-model");
    if (audit.provider) metric("Provider", asText(audit.provider), "audit-model");
    const elapsedSeconds = nonNegative(metrics.elapsed_seconds) ? Number(metrics.elapsed_seconds) : nonNegative(metrics.elapsed_ms) ? Number(metrics.elapsed_ms) / 1000 : null;
    if (elapsedSeconds !== null) metric("Run time", `${elapsedSeconds.toLocaleString("en-US", { maximumFractionDigits: 2 })} s`);
    if (nonNegative(metrics.model_calls)) metric("Model calls", asText(metrics.model_calls));
    if (nonNegative(metrics.tool_calls)) metric("Tool calls", asText(metrics.tool_calls));
    list(audit.tool_trace).forEach((call, index) => {
      if (!call || typeof call !== "object") return;
      const row = node("li", "audit-trace-row");
      const number = node("span", "audit-trace-number", String(index + 1).padStart(2, "0"));
      number.setAttribute("aria-hidden", "true");
      row.append(number, node("span", "audit-tool-name", call.tool || "Unnamed tool"), node("span", "audit-tool-status", call.status || "Status not reported"));
      trace.append(row);
    });
    trace.hidden = !trace.children.length;
    byId("audit-note").textContent = metadata.children.length || trace.children.length
      ? "Reported by the completed backend run. Source inputs are omitted from this view."
      : "No model or tool audit metadata was returned for this run.";
  }

  function renderResult(result, runId, context) {
    const previous = lastResult;
    const sameBrief = lastBrief === context.brief;
    byId("result-heading").textContent = asText(result.headline) || "Your scope is ready for review.";
    byId("result-summary").textContent = asText(result.summary);
    byId("service-name").textContent = asText(result.service_name) || "No catalog match confirmed";
    const quote = result.quote || {};
    byId("quote-total").textContent = money(quote.total, quote.currency || result.currency);
    const priceNotes = asText(quote.notes);
    byId("quote-notes").textContent = priceNotes || "Synthetic catalog price only. Confirm actual scope, price, and terms before agreeing work.";
    renderScope(list(result.scope_items));
    renderQuestions(list(result.questions));
    renderRisks(list(result.risks));
    const deliverables = list(result.deliverables);
    const deliverableList = byId("deliverables-list");
    deliverableList.replaceChildren();
    deliverables.forEach((item) => deliverableList.append(node("li", "", item)));
    byId("deliverables-section").hidden = !deliverables.length;
    replyText = asText(result.client_message);
    byId("client-message").textContent = replyText || "No reply was returned. Review the scope and write your client reply.";
    byId("copy-reply").disabled = !replyText;
    byId("copy-reply-label").textContent = "Copy reply";
    const metrics = result.metrics || {};
    const checked = Number(metrics.grounded_evidence_count);
    byId("result-metrics").textContent = Number.isFinite(checked) && metrics.grounded_evidence_count !== null && metrics.grounded_evidence_count !== undefined
      ? `${checked} source ${checked === 1 ? "quote" : "quotes"} checked. Evidence matching verifies provenance, not meaning. Review before sharing.`
      : "Check every boundary and source quote before sharing.";
    renderComparison(previous, result, sameBrief);
    renderAudit(result);
    lastResult = result;
    lastRunId = runId;
    lastBrief = context.brief;
    ui.export.href = `/api/runs/${encodeURIComponent(runId)}/download`;
    ui.export.setAttribute("download", "scopeproof-review-pack.zip");
    ui.export.setAttribute("aria-disabled", "false");
    ui.export.removeAttribute("tabindex");
    ui.result.hidden = false;
    ui.result.classList.remove("stale-result");
    ui.empty.hidden = true;
    byId("result-heading").setAttribute("tabindex", "-1");
    byId("result-heading").focus({ preventScroll: true });
  }

  async function poll(runId, version, context, failures = 0) {
    if (version !== currentRequest) return;
    try {
      const run = await request(`/api/runs/${encodeURIComponent(runId)}`);
      if (version !== currentRequest) return;
      renderRun(run);
      if (run.status === "complete") {
        if (!run.result || typeof run.result !== "object") throw new Error("The run ended without a readable result. No new draft has been displayed.");
        renderResult(run.result, runId, context);
        setBusy(false);
        toast("Your scope is ready for review.");
      } else if (run.status === "failed") {
        setBusy(false);
        byId("run-panel-footnote").textContent = lastResult ? "Your previous draft is still available below. This run produced no new scope or price." : "This run produced no scope or price. Your brief is still in the editor.";
      } else if (run.status === "queued" || run.status === "running") {
        pollTimer = setTimeout(() => poll(runId, version, context), 1100);
      } else throw new Error("The backend returned an unknown run state. No new result has been displayed.");
    } catch (error) {
      if (version !== currentRequest) return;
      if (failures < 2 && !error.status) {
        ui.runStage.textContent = "The connection was interrupted. Checking the same run again…";
        pollTimer = setTimeout(() => poll(runId, version, context, failures + 1), 2000);
        return;
      }
      renderRun({ status: "failed", stage: "Unable to retrieve this run", events: [], error: `${error.message} The backend may still be working; no completed result could be verified.` });
      setBusy(false);
    }
  }

  ui.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (running) return;
    const brief = ui.brief.value.trim();
    const change = ui.change.value.trim();
    if (brief.length < 20) {
      ui.error.textContent = "Add a little more context—at least 20 characters—so there is a brief to review.";
      ui.error.hidden = false;
      ui.brief.focus();
      return;
    }
    if (brief.length + change.length > 12000 || change.length > 4000) {
      ui.error.textContent = "Keep both fields together within 12,000 characters, with no more than 4,000 in the change request.";
      ui.error.hidden = false;
      return;
    }
    const version = ++currentRequest;
    clearTimeout(pollTimer);
    ui.error.hidden = true;
    ui.runError.hidden = true;
    ui.runError.textContent = "";
    ui.events.replaceChildren();
    ui.run.hidden = false;
    ui.run.classList.remove("is-complete", "is-failed");
    ui.empty.hidden = true;
    byId("run-heading").textContent = "Sending your brief.";
    byId("run-state-badge").textContent = "Connecting";
    byId("run-state-badge").className = "run-state-badge";
    ui.runStage.textContent = "Requesting a real run from the local backend.";
    byId("run-panel-footnote").textContent = "These steps come from the live run. Your draft appears when the checks finish.";
    setBusy(true);
    if (window.matchMedia("(max-width: 710px)").matches) ui.run.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const body = { brief };
      if (change) body.change_request = change;
      const started = await request("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (version !== currentRequest) return;
      if (!started.id) throw new Error("The backend did not return a run identifier. No result has been created in this page.");
      renderRun({ ...started, events: [] });
      await poll(asText(started.id), version, { brief, change });
    } catch (error) {
      if (version !== currentRequest) return;
      renderRun({ status: "failed", stage: "The run could not start", events: [], error: error.message });
      byId("run-panel-footnote").textContent = lastResult ? "Your previous draft is still available below. No new draft has been created." : "Your brief is still in the editor. Check the connection and try again.";
      setBusy(false);
      loadHealth();
    }
  });

  ui.brief.addEventListener("input", updateCount);
  ui.change.addEventListener("input", () => { ui.error.hidden = true; });
  ui.clear.addEventListener("click", () => {
    if (running) return;
    ui.brief.value = "";
    ui.change.value = "";
    ui.changeDetails.open = false;
    updateCount();
    ui.brief.focus();
  });
  byId("refresh-health").addEventListener("click", loadHealth);
  byId("copy-reply").addEventListener("click", async () => {
    if (!replyText) return;
    try {
      await navigator.clipboard.writeText(replyText);
      byId("copy-reply-label").textContent = "Copied";
      toast("Reply copied. Review it before sending.");
      setTimeout(() => { byId("copy-reply-label").textContent = "Copy reply"; }, 2200);
    } catch (_) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(byId("client-message"));
      selection.removeAllRanges();
      selection.addRange(range);
      toast("Reply selected. Use your browser’s Copy command.");
    }
  });
  ui.export.addEventListener("click", (event) => {
    if (!lastRunId || ui.export.getAttribute("aria-disabled") === "true") event.preventDefault();
  });
  window.addEventListener("beforeunload", () => clearTimeout(pollTimer));

  updateCount();
  Promise.allSettled([loadHealth(), loadCatalog(), loadExamples()]);
})();
