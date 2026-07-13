from __future__ import annotations

from html import escape

from fastapi.responses import HTMLResponse


SUPPORT_EMAIL = "shreelakshmiastro@gmail.com"
SUPPORT_PHONES = ["9142327953", "9004412112"]

POLICY_LINKS = [
    ("Return Policy", "/return-policy"),
    ("Refund Policy", "/refund-policy"),
    ("Privacy Policy", "/privacy-policy"),
    ("Disclaimer", "/disclaimer"),
    ("About & Contact", "/about-contact"),
]

POLICY_COPY = {
    "return": {
        "title": "Return Policy",
        "eyebrow": "Service policy",
        "intro": "Shree Lakshmi Astro provides digital astrology consultations, Prashna reports, matchmaking analysis, and related advisory services. Since these are service-based and digital offerings, physical product returns do not apply.",
        "sections": [
            (
                "Digital service delivery",
                [
                    "Consultation requests, generated reports, appointment confirmations, and chart-based insights are delivered digitally through the application, email, phone, WhatsApp, or an online meeting link.",
                    "Once a consultation, report generation, or astrologer review has started, the service is considered in progress and cannot be returned like a physical product.",
                ],
            ),
            (
                "Incorrect booking details",
                [
                    "Customers are responsible for entering accurate name, date of birth, time of birth, place of birth, question, and contact details.",
                    "If you notice an error before the consultation or report work begins, contact support immediately so we can try to update the booking.",
                ],
            ),
            (
                "Support window",
                [
                    "For any delivery or access issue, please contact us within 48 hours of payment or booking confirmation.",
                    "We will review the case and help with rescheduling, correction, or escalation where reasonably possible.",
                ],
            ),
        ],
    },
    "refund": {
        "title": "Refund Policy",
        "eyebrow": "Payment and cancellation",
        "intro": "This refund policy is designed for paid consultation and digital astrology services, including future payment gateway integration.",
        "sections": [
            (
                "Eligible refunds",
                [
                    "A refund may be considered if payment was deducted but no booking was created, the service was not delivered due to a confirmed technical issue, or Shree Lakshmi Astro cancels the paid consultation and cannot offer a suitable replacement slot.",
                    "Duplicate payments for the same booking are eligible for review and refund after payment verification.",
                ],
            ),
            (
                "Non-refundable cases",
                [
                    "Payments are generally non-refundable once the astrologer has started reviewing the chart, the consultation has been completed, or a personalized report has been generated.",
                    "Refunds may be declined if the customer provided incorrect birth details, missed the scheduled consultation without prior notice, or requested cancellation after work had begun.",
                ],
            ),
            (
                "Refund timeline",
                [
                    "Approved refunds are initiated to the original payment method where possible.",
                    "Bank, UPI, card, or payment gateway settlement timelines may vary, but approved refunds are usually processed within 7 to 10 working days after verification.",
                ],
            ),
        ],
    },
    "privacy": {
        "title": "Privacy Policy",
        "eyebrow": "Customer data protection",
        "intro": "We respect the privacy of users who share personal, birth, consultation, and payment-related information with Shree Lakshmi Astro. Birth date, birth time, and birth location are treated as highly sensitive personal information.",
        "sections": [
            (
                "Information we collect",
                [
                    "We may collect your name, email address, phone number, date of birth, time of birth, place of birth, consultation question, payment status, and booking history.",
                    "For application security and reliability, we may also process technical information such as request identifiers, session status, device/browser data, and usage logs.",
                ],
            ),
            (
                "Protection of birth-related data",
                [
                    "Birth date, exact birth time, and birth location can reveal deeply personal information. We handle this data with additional care and use it only for astrology chart generation, consultation preparation, customer support, and service records connected to your request.",
                    "Sensitive birth-related data should be protected in transit through HTTPS/TLS and protected at rest using strong encryption practices such as AES-256 or equivalent controls where applicable.",
                ],
            ),
            (
                "How information is used",
                [
                    "Your information is used to generate astrology charts, manage consultations, verify payments, contact you about your booking, improve service quality, and maintain platform security.",
                    "We do not sell personal birth or consultation data. Access is limited to authorized team members or service providers who need it to deliver the requested service.",
                ],
            ),
            (
                "Anonymous and limited-use options",
                [
                    "Where a feature does not require a full birth profile or paid consultation record, we aim to support basic or limited usage without asking for unnecessary personal details.",
                    "Customers may choose not to submit optional information. Some features, such as birth-chart generation or personalized consultation, may require birth details to function correctly.",
                ],
            ),
            (
                "Consent and privacy rights",
                [
                    "We follow a compliance-first approach inspired by privacy laws such as GDPR, CCPA, and other applicable data protection requirements. This includes transparent consent flows, opt-in permissions where required, and clear information about how personal data is used.",
                    "Depending on your location and applicable law, you may request access, correction, deletion, restriction, or portability of your personal information, subject to legal, audit, fraud-prevention, dispute-resolution, and service-record requirements.",
                ],
            ),
            (
                "Payment information",
                [
                    "When online payments are enabled, payment processing may be handled by a third-party payment gateway.",
                    "Sensitive card, UPI, or banking credentials should be entered only on the secure payment gateway page. Shree Lakshmi Astro should not store full card or banking credentials in the application.",
                ],
            ),
            (
                "Data requests",
                [
                    "You may contact us to request correction, access, or deletion of your personal information, subject to legal, audit, dispute-resolution, and service-record requirements.",
                ],
            ),
        ],
    },
    "disclaimer": {
        "title": "Disclaimer",
        "eyebrow": "Important notice",
        "intro": "Shree Lakshmi Astro provides astrology-based guidance and digital consultation support. The information shared through this platform should be used for reflection and personal decision support.",
        "sections": [
            (
                "No guaranteed outcome",
                [
                    "Astrological readings, Prashna analysis, matchmaking observations, predictions, and remedies are interpretive in nature and do not guarantee any specific event, result, profit, relationship outcome, health outcome, job, visa, legal result, or financial gain.",
                ],
            ),
            (
                "Professional advice",
                [
                    "Our services are not a substitute for qualified medical, legal, financial, psychological, or professional advice.",
                    "For health, legal, investment, emergency, or high-risk matters, please consult an appropriately qualified professional before making decisions.",
                ],
            ),
            (
                "Customer responsibility",
                [
                    "Customers are responsible for the choices they make after receiving guidance.",
                    "The accuracy of any astrology interpretation depends partly on the accuracy of birth time, birth place, question context, and other details provided by the customer.",
                ],
            ),
        ],
    },
}


def _nav(active_path: str) -> str:
    links = [
        ("Home", "/index.html"),
        ("Consultant", "/consultation"),
        ("Pricing", "/index.html#pricing"),
        ("About", "/about.html"),
        ("Astro Community", "/astro-community"),
    ]
    link_html = "\n".join(
        f'<a href="{href}" class="nav-btn{" active" if href == active_path else ""}">{escape(label)}</a>'
        for label, href in links
    )
    return f"""
      <nav class="global-navbar" aria-label="Main Navigation">
        <div class="logo-text">
          <a href="/index.html" style="text-decoration:none;color:inherit;display:flex;align-items:center">
            <img src="/ganesha.png" alt="Ganesha Logo" class="navbar-ganesha" />
            Shree Lakshmi<span class="highlight">Astro</span>
          </a>
        </div>
        <div class="nav-links" id="desktop-navigation">
          {link_html}
        </div>
        <div class="nav-auth">
          <span class="profile-avatar-trigger" aria-label="User profile">U</span>
        </div>
      </nav>
    """


def _policy_nav(active_path: str) -> str:
    links = "\n".join(
        f'<a href="{href}" class="{"active" if href == active_path else ""}">{escape(label)}</a>'
        for label, href in POLICY_LINKS
    )
    return f"""
      <nav class="legal-policy-nav" aria-label="Policy pages">
        <span>Website policies</span>
        {links}
      </nav>
    """


def _icon(name: str) -> str:
    if name == "mail":
        return '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="16" x="2" y="4" rx="2"></rect><path d="m22 7-10 6L2 7"></path></svg>'
    if name == "phone":
        return '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.08 4.18 2 2 0 0 1 4.06 2h3a2 2 0 0 1 2 1.72c.13.96.35 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.35 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>'
    if name == "send":
        return '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"></path><path d="M22 2 11 13"></path></svg>'
    return ""


def _contact_panel() -> str:
    phone_links = "\n".join(
        f'<a href="tel:+91{phone}" class="legal-contact-link">{_icon("phone")}<span>+91 {phone}</span></a>'
        for phone in SUPPORT_PHONES
    )
    return f"""
      <aside class="legal-contact-panel" aria-label="Contact Shree Lakshmi Astro">
        <h2>Contact Us</h2>
        <p>For booking, payment, refund, privacy, or support queries, reach us using the official contact details below.</p>
        <div class="legal-contact-links">
          <a href="mailto:{SUPPORT_EMAIL}" class="legal-contact-link">{_icon("mail")}<span>{SUPPORT_EMAIL}</span></a>
          {phone_links}
        </div>
      </aside>
    """


def _contact_form() -> str:
    return f"""
      <form class="contact-form" data-contact-form>
        <div class="contact-form-grid">
          <label><span>Full name</span><input name="name" autocomplete="name" required /></label>
          <label><span>Email address</span><input name="email" type="email" autocomplete="email" required /></label>
          <label><span>Phone number</span><input name="phone" autocomplete="tel" /></label>
          <label>
            <span>Support topic</span>
            <select name="topic">
              <option>Payment or refund</option>
              <option>Booking support</option>
              <option>Consultation query</option>
              <option>Privacy request</option>
              <option>Other</option>
            </select>
          </label>
        </div>
        <label>
          <span>Message</span>
          <textarea name="message" rows="7" placeholder="Write your booking ID, payment reference, and the issue you need help with." required></textarea>
        </label>
        <button type="submit" class="contact-submit">{_icon("send")}<span>Send Email</span></button>
        <p class="contact-form-note">This opens your email app with the message filled in, so you can review and send it directly to our support team.</p>
      </form>
    """


def _footer() -> str:
    policy_links = "\n".join(f'<li><a href="{href}">{escape(label)}</a></li>' for label, href in POLICY_LINKS)
    return f"""
      <footer class="app-footer" aria-label="Website footer">
        <div class="footer-grid">
          <section class="footer-col about-col">
            <div class="footer-logo">
              <div class="logo-brush">
                <span class="logo-text-top">Shree Lakshmi</span>
                <span class="logo-text-bottom">Astro</span>
              </div>
            </div>
            <h3>ABOUT US</h3>
            <p>Shree Lakshmi Astro provides Research-Level Vedic Astrology Consultations & Predictions. Get Expert Vedic guidance on Career, Health, Relationships & more.</p>
          </section>
          <section class="footer-col links-col">
            <h3>QUICK LINKS</h3>
            <ul class="quick-links-list">
              <li><a href="/community/apply">Shree Lakshmi Astro Community (Astrologers)</a></li>
              {policy_links}
            </ul>
            <h3 class="social-title">SOCIAL CHANNELS</h3>
            <div class="social-channels">
              <a href="#" class="social-icon" title="Instagram" aria-label="Instagram">IG</a>
              <a href="#" class="social-icon" title="Facebook" aria-label="Facebook">FB</a>
              <a href="#" class="social-icon" title="Twitter" aria-label="Twitter">X</a>
              <a href="#" class="social-icon" title="YouTube" aria-label="YouTube">YT</a>
            </div>
          </section>
          <section class="footer-col community-col">
            <p class="community-text">Join Shree Lakshmi Astro's WhatsApp for daily astrology insights. Enhance your success with our expert predictions.</p>
            <a href="https://whatsapp.com/channel/0029Vb8ZvHsKbYMLie7XIk0A" target="_blank" rel="noreferrer" class="btn-whatsapp-community">
              <svg class="wa-icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.27-1.38a9.9 9.9 0 0 0 4.72 1.2h.01c5.46 0 9.91-4.45 9.91-9.91S17.5 2 12.04 2Zm5.77 14.17c-.24.68-1.38 1.3-1.94 1.35-.5.05-1.13.07-1.82-.11-.42-.13-.96-.31-1.65-.61-2.9-1.25-4.79-4.16-4.94-4.35-.14-.19-1.18-1.57-1.18-3 0-1.43.75-2.13 1.02-2.42.27-.29.59-.36.78-.36h.56c.18 0 .42-.07.66.5.24.58.84 2.02.91 2.16.08.15.13.32.03.51-.09.19-.14.31-.29.48-.14.17-.3.38-.43.51-.14.14-.29.3-.12.59.17.29.75 1.24 1.61 2.01 1.11.99 2.05 1.3 2.34 1.44.29.15.46.12.63-.07.17-.19.72-.84.91-1.13.19-.29.39-.24.66-.14.27.1 1.7.8 1.99.95.29.14.48.22.55.34.07.12.07.7-.17 1.35Z"/></svg>
              <span>Join WhatsApp Community</span>
            </a>
          </section>
        </div>
        <div class="footer-bottom">
          <p>(c) 2026 Shree Lakshmi Astro. All Rights Reserved</p>
        </div>
      </footer>
    """


def _document_sections(page_key: str) -> str:
    page = POLICY_COPY[page_key]
    sections = []
    for title, paragraphs in page["sections"]:
        body = "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        sections.append(f'<section class="legal-section"><h2>{escape(title)}</h2>{body}</section>')
    sections.append(_contact_panel())
    return "\n".join(sections)


def _about_contact() -> str:
    return f"""
      <main class="app-page legal-page">
        <section class="legal-hero">
          <div>
            <p class="legal-eyebrow">About & Contact</p>
            <h1>Shree Lakshmi Astro</h1>
            <p>Shree Lakshmi Astro is a digital astrology platform for Prashna Kundli, birth-chart based consultation, matchmaking support, and astrologer-led guidance. The application is being prepared for real-world paid consultation workflows with clear customer support, policy, and payment-compliance pages.</p>
          </div>
        </section>
        <section class="legal-document-layout">
          {_policy_nav("/about-contact")}
          <div class="legal-document">
            <section class="legal-section">
              <h2>What we provide</h2>
              <p>We help customers submit birth details, consultation questions, Prashna details, and matchmaking information so the astrologer can review the case with better context and maintain service history.</p>
            </section>
            <section class="legal-section">
              <h2>Customer support</h2>
              <p>Please include your name, registered phone number, email address, booking ID or payment reference, and a short description of the issue when contacting support.</p>
            </section>
            <section class="legal-section legal-section--contact">
              <div>
                <h2>Send us a message</h2>
                <p>Use this form for booking, payment, refund, privacy, or consultation support. It prepares an email with your details so the support team receives a clear request.</p>
              </div>
              {_contact_form()}
            </section>
            {_contact_panel()}
          </div>
        </section>
      </main>
    """


def _page_shell(title: str, path: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(title)} | Shree Lakshmi Astro</title>
    <link rel="stylesheet" href="/styles.css?v=16" />
    <link rel="stylesheet" href="/legal-policy.css?v=2" />
  </head>
  <body class="legal-static-shell">
    {_nav(path)}
    {body}
    {_footer()}
    <script src="/legal-policy.js?v=1"></script>
  </body>
</html>"""


def render_legal_page(page_key: str) -> HTMLResponse:
    if page_key == "about-contact":
        return HTMLResponse(_page_shell("About & Contact", "/about-contact", _about_contact()))

    page = POLICY_COPY[page_key]
    path = f"/{page_key}-policy" if page_key != "disclaimer" else "/disclaimer"
    body = f"""
      <main class="app-page legal-page">
        <section class="legal-hero">
          <div>
            <p class="legal-eyebrow">{escape(page["eyebrow"])}</p>
            <h1>{escape(page["title"])}</h1>
            <p>{escape(page["intro"])}</p>
            <p class="legal-updated">Last updated: July 13, 2026</p>
          </div>
        </section>
        <section class="legal-document-layout">
          {_policy_nav(path)}
          <div class="legal-document">
            {_document_sections(page_key)}
          </div>
        </section>
      </main>
    """
    return HTMLResponse(_page_shell(page["title"], path, body))
