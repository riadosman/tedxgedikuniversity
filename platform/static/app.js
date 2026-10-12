"use strict";
for (const [id, className] of [["mobile-menu", "nav-open"], ["public-menu", "public-nav-open"]]) {
  const button = document.getElementById(id);
  if (!button) continue;
  const navigation = document.getElementById(button.getAttribute("aria-controls"));
  const close = () => {document.body.classList.remove(className); button.setAttribute("aria-expanded", "false");};
  button.addEventListener("click", () => {
    const open = document.body.classList.toggle(className);
    button.setAttribute("aria-expanded", String(open));
    if (open) navigation.querySelector("a, button")?.focus();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.body.classList.contains(className)) {close(); button.focus();}
  });
  document.addEventListener("click", event => {
    if (!navigation.contains(event.target) && !button.contains(event.target)) close();
  });
  document.addEventListener("focusin", event => {
    if (!navigation.contains(event.target) && !button.contains(event.target)) close();
  });
}
for (const dropdown of document.querySelectorAll(".language-menu, .context-tabs details")) {
  document.addEventListener("click", event => { if (!dropdown.contains(event.target)) dropdown.open = false; });
  dropdown.addEventListener("keydown", event => {
    if (event.key === "Escape" && dropdown.open) { dropdown.open = false; dropdown.querySelector("summary").focus(); }
  });
}
const confirmation = document.getElementById("confirmation");
let pendingForm, pendingSubmitter;
const confirmedForms = new WeakSet();
document.querySelectorAll("form[data-confirm]").forEach(form => form.addEventListener("submit", event => {
  if (confirmedForms.has(form)) return;
  event.preventDefault();
  pendingForm = form; pendingSubmitter = event.submitter;
  document.getElementById("confirmation-message").textContent = form.dataset.confirm;
  document.getElementById("confirmation-accept").textContent = event.submitter?.textContent || gettext("Confirm");
  confirmation.showModal();
}));
document.getElementById("confirmation-cancel").addEventListener("click", () => confirmation.close());
document.getElementById("confirmation-accept").addEventListener("click", () => {
  const form = pendingForm, submitter = pendingSubmitter;
  confirmation.close();
  if (form) { confirmedForms.add(form); form.requestSubmit(submitter); }
});
confirmation.addEventListener("close", () => { pendingForm = null; pendingSubmitter = null; });
document.querySelectorAll("form:not(#scan-form):not(#lookup-form)").forEach(form => form.addEventListener("submit", event => {
  if (event.defaultPrevented) return;
  if (form.querySelector('input[name="action"][value="export"]') || /\/export\/$/.test(form.action)) return;
  if (form.dataset.submitting === "true") { event.preventDefault(); return; }
  form.dataset.submitting = "true";
  form.setAttribute("aria-busy", "true");
  const button = event.submitter;
  // Keep named submitters successful: disabling them drops their value from POST.
  if (button) { button.setAttribute("aria-disabled", "true"); button.textContent = gettext("Working…"); }
}));

document.getElementById("print-ticket")?.addEventListener("click", () => window.print());
// The plate is asked only from attendees who answer "Yes" to arriving by car.
document.querySelectorAll("[data-show-when-car]").forEach(plate => {
  const field = plate.closest(".form-field");
  const choices = plate.form.querySelectorAll('input[name="arrives_by_car"]');
  const sync = () => {
    const byCar = plate.form.querySelector('input[name="arrives_by_car"]:checked')?.value === "yes";
    field.hidden = !byCar;
    plate.required = byCar;
  };
  choices.forEach(choice => choice.addEventListener("change", sync));
  sync();
});
window.addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
const firstInvalid = document.querySelector('[aria-invalid="true"]');
if (firstInvalid) { for (let parent=firstInvalid.parentElement;parent;parent=parent.parentElement) { if(parent.tagName === "DETAILS") parent.open=true; } firstInvalid.focus(); }

const dashboard = document.getElementById("live-dashboard");
if (dashboard) {
  const feedback = document.getElementById("dashboard-freshness");
  let updating = false;
  async function refreshDashboard() {
    if (updating || dashboard.contains(document.activeElement)) return;
    updating = true; dashboard.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(location.href, {credentials:"same-origin", signal:AbortSignal.timeout(8000)});
      if (!response.ok || response.redirected) throw new Error();
      const documentCopy = new DOMParser().parseFromString(await response.text(), "text/html");
      const content = documentCopy.getElementById("live-dashboard");
      if (!content) throw new Error();
      if (!dashboard.contains(document.activeElement)) { const expanded = dashboard.querySelector(".operations-details")?.open; dashboard.replaceChildren(...content.childNodes); const details = dashboard.querySelector(".operations-details"); if(details) details.open=expanded; }
      feedback.textContent = gettext("Dashboard updated.");
    } catch { feedback.textContent = gettext("Updates unavailable. Displayed information may be stale."); }
    finally { updating = false; dashboard.setAttribute("aria-busy", "false"); }
  }
  document.getElementById("refresh-dashboard").addEventListener("click", refreshDashboard);
  setInterval(()=>{if(document.getElementById("auto-dashboard").checked) refreshDashboard();},30000);
}
