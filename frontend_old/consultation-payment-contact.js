(function () {
  const MANAGER_PHONE = "9142327953";
  const MANAGER_WHATSAPP = "+919142327953";
  const WHATSAPP_COMMUNITY_URL = "https://whatsapp.com/channel/0029Vb8ZvHsKbYMLie7XIk0A";

  let consultantProfile = null;

  function escapeHtml(raw) {
    return String(raw || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function statusMessageFor(status) {
    if (status === "paid") {
      return "Your payment is confirmed. Please contact the manager on WhatsApp or call to fix the appointment time.";
    }
    if (status === "pending_payment") {
      return "Your consultation case has been created. Payment is required before the astrologer can fulfill it.";
    }
    if (status === "waiting_queue") {
      return "Currently, all consultation slots are full. You are in the waiting queue and will be notified when your turn comes.";
    }
    if (status === "accepted") {
      return "Your consultation request has been accepted. Please check the scheduled time and meeting link once added.";
    }
    if (status === "in_progress") return "Your consultation is currently in progress.";
    if (status === "completed") return "Your consultation has been completed.";
    if (status === "rejected") {
      return "Your consultation request was rejected. Please contact support if you need clarification.";
    }
    if (status === "cancelled") return "Your consultation request was cancelled.";
    return "Your consultation request has been received. The consultant will review it soon.";
  }

  function paymentContactBox() {
    const consultantName = consultantProfile?.name || "Rupesh Kumar";
    const configuredPhone = consultantProfile?.contact_phone || consultantProfile?.whatsapp_number || "";
    const managerPhone = configuredPhone || MANAGER_PHONE;
    const managerWhatsApp = (consultantProfile?.whatsapp_number || managerPhone || MANAGER_WHATSAPP).replace(/[^0-9]/g, "");

    return `
      <div class="paid-contact-box">
        <strong>Payment confirmed. Next step: contact the manager now.</strong>
        <div><strong>Manager number:</strong> <a href="tel:${escapeHtml(managerPhone)}">${escapeHtml(managerPhone)}</a></div>
        <div><strong>WhatsApp:</strong> <a href="https://wa.me/${escapeHtml(managerWhatsApp)}" target="_blank" rel="noopener">Message the manager</a></div>
        <div>The manager will help you fix the appointment time with ${escapeHtml(consultantName)} and share the next steps for call or Google Meet.</div>
        <div class="paid-community-notice">
          <strong>Join fast for latest updates:</strong>
          <span>Join Shree Lakshmi Astro's WhatsApp community for consultation updates, daily astrology insights, and important announcements.</span>
          <a href="${WHATSAPP_COMMUNITY_URL}" target="_blank" rel="noopener">Join WhatsApp Community</a>
        </div>
      </div>
    `;
  }

  window.renderRequestStatus = function renderRequestStatus(request, message, slotAvailable = true) {
    const resultPanel = document.getElementById("result-panel");
    const resultStatus = document.getElementById("result-status");
    const resultTitle = document.getElementById("result-title");
    const resultMessage = document.getElementById("result-message");
    const resultDetails = document.getElementById("result-details");
    if (!resultPanel || !resultStatus || !resultTitle || !resultMessage || !resultDetails) return;

    const status = request.status || request.case_status || "requested";
    const paymentStatus = request.payment_status || request.consultation?.payment_status || "not_paid";
    const displayStatus = paymentStatus === "paid" ? "paid" : status;

    resultStatus.textContent = displayStatus;
    resultStatus.className = `status-pill ${displayStatus}`;
    resultTitle.textContent = slotAvailable ? "Your request is active" : "Added to waiting queue";
    if (paymentStatus === "paid") resultTitle.textContent = "Payment confirmed";
    if (status === "accepted") resultTitle.textContent = "Your request is accepted";
    if (status === "in_progress") resultTitle.textContent = "Consultation is in progress";
    if (status === "completed") resultTitle.textContent = "Consultation completed";
    if (status === "rejected") resultTitle.textContent = "Request rejected";
    if (status === "cancelled") resultTitle.textContent = "Request cancelled";
    if (status === "waiting_queue") resultTitle.textContent = "Added to waiting queue";

    resultMessage.textContent = message || statusMessageFor(displayStatus);
    resultDetails.innerHTML = `
      ${paymentStatus === "paid" ? paymentContactBox() : ""}
      <div><strong>Request ID:</strong> ${escapeHtml(request.id || request.case_id)}</div>
      <div><strong>Request status:</strong> ${escapeHtml(status)}</div>
      <div><strong>Payment status:</strong> ${escapeHtml(paymentStatus)}</div>
      <div><strong>Queue number:</strong> ${request.queue_number ? escapeHtml(request.queue_number) : "Active slot"}</div>
      <div><strong>Submitted question:</strong> ${escapeHtml(request.question || request.consultation?.question)}</div>
      <div><strong>Consultant name:</strong> ${escapeHtml(consultantProfile?.name || "Rupesh Kumar")}</div>
      <div><strong>Scheduled date/time:</strong> ${request.scheduled_at ? escapeHtml(request.scheduled_at) : "Not scheduled yet"}</div>
      <div><strong>Meeting link:</strong> ${request.meeting_link ? `<a href="${escapeHtml(request.meeting_link)}" target="_blank" rel="noopener">${escapeHtml(request.meeting_link)}</a>` : "Not added yet"}</div>
    `;
    renderStatusActions(request, status, paymentStatus);
    resultPanel.classList.add("show");
  };

  function authHeaders(headers = {}) {
    const token = localStorage.getItem("supabase_token");
    return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
  }

  function loadRazorpayCheckout() {
    return new Promise((resolve, reject) => {
      if (window.Razorpay) {
        resolve();
        return;
      }
      const existingScript = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
      if (existingScript) {
        existingScript.addEventListener("load", resolve, { once: true });
        existingScript.addEventListener("error", reject, { once: true });
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error("Could not load Razorpay Checkout."));
      document.head.appendChild(script);
    });
  }

  function requestIdFor(request) {
    return request?.id || request?.case_id || "";
  }

  function requestEmailFor(request) {
    return request?.email || request?.user?.email || "";
  }

  function clearSavedRequestIds() {
    localStorage.removeItem("latest_consultation_request_id");
    localStorage.removeItem("latest_consultation_case_id");
  }

  function renderStatusActions(request, status, paymentStatus) {
    const actions = document.querySelector(".status-actions");
    if (!actions) return;
    const canPay = paymentStatus !== "paid" && !["cancelled", "completed", "refunded"].includes(status);
    const canCancel = canPay && ["pending_payment", "requested", "waiting_queue"].includes(status);

    actions.innerHTML = `
      ${canPay ? '<button id="pay-pending-request-btn" class="btn-submit status-action-primary" type="button">Pay Now</button>' : ""}
      <button id="refresh-status-btn" class="secondary-btn" type="button">Refresh Status</button>
      ${canCancel ? '<button id="cancel-pending-request-btn" class="secondary-btn status-action-danger" type="button">Delete Request</button>' : ""}
      <button id="clear-status-btn" class="secondary-btn" type="button">Clear Saved Request</button>
    `;

    document.getElementById("refresh-status-btn")?.addEventListener("click", refreshSavedStatusWithEnhancedRenderer);
    document.getElementById("clear-status-btn")?.addEventListener("click", () => {
      clearSavedRequestIds();
      document.getElementById("result-panel")?.classList.remove("show");
    });
    document.getElementById("pay-pending-request-btn")?.addEventListener("click", () => payPendingRequest(request));
    document.getElementById("cancel-pending-request-btn")?.addEventListener("click", () => cancelPendingRequest(request));
  }

  async function payPendingRequest(request) {
    const requestId = requestIdFor(request);
    const requesterEmail = requestEmailFor(request);
    if (!requestId) return;

    const payButton = document.getElementById("pay-pending-request-btn");
    const originalText = payButton?.textContent || "Pay Now";
    try {
      if (payButton) {
        payButton.disabled = true;
        payButton.textContent = "Opening payment...";
      }
      await loadRazorpayCheckout();
      const amountPaise = Math.max(100, Math.round(Number(consultantProfile?.consultation_fee || 1) * 100));
      const orderResponse = await fetch("/api/create-order", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          amount: amountPaise,
          currency: "INR",
          consultation_case_id: requestId,
          requester_email: requesterEmail || undefined,
          purpose: "consultation",
        }),
      });
      const order = await orderResponse.json();
      if (!orderResponse.ok) throw new Error(order.detail || "Could not create payment order.");

      const checkoutResult = await new Promise((resolve, reject) => {
        const checkout = new window.Razorpay({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: "Shree Lakshmi Astro",
          description: "Astrology consultation",
          order_id: order.order_id,
          prefill: {
            name: request.name || request.user?.full_name || "",
            email: requesterEmail,
            contact: request.phone || request.user?.mobile_number || "",
          },
          notes: { consultation_case_id: requestId },
          theme: { color: "#8c3d25" },
          modal: { ondismiss: () => reject(new Error("Payment was closed before completion.")) },
          handler: resolve,
        });
        checkout.on("payment.failed", (response) => {
          reject(new Error(response?.error?.description || "Payment failed. Please try again."));
        });
        checkout.open();
      });

      const verifyResponse = await fetch("/api/verify-payment", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          razorpay_order_id: checkoutResult.razorpay_order_id,
          razorpay_payment_id: checkoutResult.razorpay_payment_id,
          razorpay_signature: checkoutResult.razorpay_signature,
        }),
      });
      const verified = await verifyResponse.json();
      if (!verifyResponse.ok) throw new Error(verified.detail || "Payment verification failed.");

      window.renderRequestStatus(
        verified.case || { ...request, payment_status: "paid", status: "confirmed" },
        "Payment verified. You can now contact the manager for appointment timing.",
      );
    } catch (error) {
      const resultMessage = document.getElementById("result-message");
      if (resultMessage) resultMessage.textContent = error.message || "Could not complete payment.";
    } finally {
      if (payButton) {
        payButton.disabled = false;
        payButton.textContent = originalText;
      }
    }
  }

  async function cancelPendingRequest(request) {
    const requestId = requestIdFor(request);
    if (!requestId) return;
    if (!window.confirm("Delete this pending consultation request? This will cancel it and remove it from your saved request.")) {
      return;
    }

    const cancelButton = document.getElementById("cancel-pending-request-btn");
    try {
      if (cancelButton) {
        cancelButton.disabled = true;
        cancelButton.textContent = "Deleting...";
      }
      const response = await fetch(`/api/consultation/request/${encodeURIComponent(requestId)}/cancel`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ requester_email: requestEmailFor(request) || undefined }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Could not delete request.");

      clearSavedRequestIds();
      window.renderRequestStatus(data.request || { ...request, status: "cancelled", payment_status: "cancelled" }, "Request deleted.");
    } catch (error) {
      const resultMessage = document.getElementById("result-message");
      if (resultMessage) resultMessage.textContent = error.message || "Could not delete request.";
    } finally {
      if (cancelButton) {
        cancelButton.disabled = false;
        cancelButton.textContent = "Delete Request";
      }
    }
  }

  async function fetchSavedConsultation(id) {
    const endpoints = [
      `/api/consultation/request/${encodeURIComponent(id)}`,
      `/api/consultation-cases/${encodeURIComponent(id)}`,
    ];
    for (const endpoint of endpoints) {
      const response = await fetch(endpoint, { headers: authHeaders(), cache: "no-store" });
      const data = await response.json().catch(() => ({}));
      if (response.ok) return data.request || data.case;
      if (response.status !== 404) break;
    }
    return null;
  }

  async function refreshSavedStatusWithEnhancedRenderer() {
    const savedIds = [
      localStorage.getItem("latest_consultation_request_id"),
      localStorage.getItem("latest_consultation_case_id"),
    ].filter(Boolean);
    for (const id of savedIds) {
      const request = await fetchSavedConsultation(id).catch(() => null);
      if (request) {
        window.renderRequestStatus(request);
        return;
      }
    }
    suppressLegacyMissingRequestCard();
  }

  function suppressLegacyMissingRequestCard() {
    const resultPanel = document.getElementById("result-panel");
    const resultStatus = document.getElementById("result-status");
    const resultTitle = document.getElementById("result-title");
    const resultMessage = document.getElementById("result-message");
    const resultDetails = document.getElementById("result-details");
    const title = (resultTitle?.textContent || "").trim().toLowerCase();
    const status = (resultStatus?.textContent || "").trim().toLowerCase();
    if (!resultPanel || (title !== "could not load saved request" && status !== "not found")) return;
    resultPanel.classList.remove("show");
    if (resultStatus) resultStatus.textContent = "pending";
    if (resultTitle) resultTitle.textContent = "Request received";
    if (resultMessage) resultMessage.textContent = "";
    if (resultDetails) resultDetails.innerHTML = "";
  }

  suppressLegacyMissingRequestCard();
  setTimeout(suppressLegacyMissingRequestCard, 100);
  setTimeout(suppressLegacyMissingRequestCard, 500);

  fetch("/api/consultation/profile")
    .then((response) => (response.ok ? response.json() : null))
    .then((data) => {
      consultantProfile = data?.consultant || null;
      refreshSavedStatusWithEnhancedRenderer();
    })
    .catch(() => {
      refreshSavedStatusWithEnhancedRenderer();
    });
})();
