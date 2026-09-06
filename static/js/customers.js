document.addEventListener("DOMContentLoaded", () => {
  const customerType = document.getElementById("id_customer_type");
  const documentType = document.getElementById("id_document_type");
  const personFields = document.querySelectorAll("[data-person-field]");
  const businessFields = document.querySelectorAll("[data-business-field]");

  function updateFields() {
    if (!customerType) return;
    const isBusiness = customerType.value === "BUSINESS";
    personFields.forEach((element) => element.classList.toggle("d-none", isBusiness));
    businessFields.forEach((element) => element.classList.toggle("d-none", !isBusiness));
    if (documentType) {
      documentType.value = isBusiness ? "RUC" : (documentType.value === "RUC" ? "DNI" : documentType.value);
    }
  }

  customerType?.addEventListener("change", updateFields);
  updateFields();
});
