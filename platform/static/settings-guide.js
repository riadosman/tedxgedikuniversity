"use strict";
document.querySelectorAll("[data-setup-field]").forEach(step => {
  const input = document.getElementById(step.dataset.setupField);
  const state = step.querySelector(".setup-state");
  const update = () => {
    const complete = input.type === "checkbox" ? input.checked : input.value.trim().length > 0;
    state.textContent = complete ? state.dataset.complete : state.dataset.missing;
    state.classList.toggle("is-complete", complete);
  };
  input.addEventListener("input", update);
  input.addEventListener("change", update);
  update();
});
document.querySelectorAll('.page-links a[href^="#"], .setup-guide a[href^="#"], .error-summary a[href^="#"]').forEach(link => {
  link.addEventListener("click", () => {
    const input = document.getElementById(link.hash.slice(1));
    if (input) {
      let parent = input.parentElement;
      while (parent) {if (parent.tagName === "DETAILS") parent.open = true; parent = parent.parentElement;}
      input.focus();
    }
  });
});
document.querySelector(".error-summary")?.focus();

// Native browser validation must be able to focus fields inside collapsed sections.
document.querySelector(".settings-form")?.addEventListener("invalid", event => {
  let parent = event.target.parentElement;
  while (parent) {if (parent.tagName === "DETAILS") parent.open = true; parent = parent.parentElement;}
}, true);
