document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("package-forms");
  const totalForms = document.getElementById("id_packages-TOTAL_FORMS");
  const template = document.getElementById("empty-package-template");
  const addButton = document.getElementById("add-package");

  const numberValue = (form, name) => {
    const input = form.querySelector(`[name$="-${name}"]`);
    return Math.max(0, Number.parseFloat(input?.value || "0") || 0);
  };

  const activeForms = () => [...container.querySelectorAll("[data-package-form]")].filter((form) => !form.classList.contains("d-none"));

  function calculateForm(form) {
    const quantity = numberValue(form, "quantity");
    const weight = numberValue(form, "weight");
    const length = numberValue(form, "length");
    const width = numberValue(form, "width");
    const height = numberValue(form, "height");
    const volumetric = (length * width * height) / 6000;
    const billable = Math.max(weight, volumetric) * quantity;
    form.querySelector("[data-volume]").textContent = `${volumetric.toFixed(2)} kg`;
    form.querySelector("[data-billable]").textContent = `${billable.toFixed(2)} kg`;
    return { quantity, actual: weight * quantity, billable };
  }

  function refreshSummary() {
    let packages = 0;
    let actual = 0;
    let billable = 0;
    activeForms().forEach((form, index) => {
      const label = form.querySelector(".package-number");
      if (label) label.textContent = `Paquete ${index + 1}`;
      const values = calculateForm(form);
      packages += values.quantity;
      actual += values.actual;
      billable += values.billable;
    });
    document.getElementById("summary-packages").textContent = packages;
    document.getElementById("summary-weight").textContent = `${actual.toFixed(2)} kg`;
    document.getElementById("summary-billable").textContent = `${billable.toFixed(2)} kg`;
  }

  function bindForm(form) {
    form.querySelectorAll("input, select").forEach((input) => input.addEventListener("input", refreshSummary));
    form.querySelector(".remove-package")?.addEventListener("click", () => {
      if (activeForms().length <= 1) {
        window.alert("El envío debe conservar al menos un paquete.");
        return;
      }
      const deleteInput = form.querySelector('[name$="-DELETE"]');
      if (deleteInput) deleteInput.checked = true;
      form.classList.add("d-none");
      refreshSummary();
    });
  }

  addButton?.addEventListener("click", () => {
    const index = Number.parseInt(totalForms.value, 10);
    const html = template.innerHTML.replaceAll("__prefix__", String(index));
    container.insertAdjacentHTML("beforeend", html);
    totalForms.value = index + 1;
    bindForm(container.lastElementChild);
    refreshSummary();
    container.lastElementChild.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  container?.querySelectorAll("[data-package-form]").forEach(bindForm);

  const costInputs = ["id_shipping_cost", "id_insurance_cost", "id_discount"];
  function refreshCost() {
    const value = (id) => Math.max(0, Number.parseFloat(document.getElementById(id)?.value || "0") || 0);
    const total = value("id_shipping_cost") + value("id_insurance_cost") - value("id_discount");
    document.getElementById("cost-total").textContent = Math.max(0, total).toFixed(2);
  }
  costInputs.forEach((id) => document.getElementById(id)?.addEventListener("input", refreshCost));
  refreshSummary();
  refreshCost();
});
