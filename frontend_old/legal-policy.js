document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.matches("[data-contact-form]")) return;

  event.preventDefault();

  const data = new FormData(form);
  const name = String(data.get("name") || "").trim();
  const email = String(data.get("email") || "").trim();
  const phone = String(data.get("phone") || "").trim();
  const topic = String(data.get("topic") || "").trim();
  const message = String(data.get("message") || "").trim();
  const subject = encodeURIComponent(`Website enquiry: ${topic || "Support request"}`);
  const body = encodeURIComponent([
    `Name: ${name}`,
    `Email: ${email}`,
    `Phone: ${phone || "Not provided"}`,
    `Topic: ${topic || "General enquiry"}`,
    "",
    "Message:",
    message,
  ].join("\n"));

  window.location.href = `mailto:shreelakshmiastro@gmail.com?subject=${subject}&body=${body}`;
});
