import React from 'react';
import { Link } from 'react-router-dom';
import { Mail, Phone, Send } from 'lucide-react';

type LegalPageKind = 'return' | 'refund' | 'privacy' | 'disclaimer' | 'about-contact';

const supportEmail = 'shreelakshmiastro@gmail.com';
const supportPhones = ['9142327953', '9004412112'];

const policyLinks = [
  { label: 'Return Policy', to: '/return-policy' },
  { label: 'Refund Policy', to: '/refund-policy' },
  { label: 'Privacy Policy', to: '/privacy-policy' },
  { label: 'Disclaimer', to: '/disclaimer' },
  { label: 'About & Contact', to: '/about-contact' },
];

const pageCopy: Record<Exclude<LegalPageKind, 'about-contact'>, {
  title: string;
  eyebrow: string;
  intro: string;
  sections: Array<{ title: string; body: string[] }>;
}> = {
  return: {
    title: 'Return Policy',
    eyebrow: 'Service policy',
    intro: 'Shree Lakshmi Astro provides digital astrology consultations, Prashna reports, matchmaking analysis, and related advisory services. Since these are service-based and digital offerings, physical product returns do not apply.',
    sections: [
      {
        title: 'Digital service delivery',
        body: [
          'Consultation requests, generated reports, appointment confirmations, and chart-based insights are delivered digitally through the application, email, phone, WhatsApp, or an online meeting link.',
          'Once a consultation, report generation, or astrologer review has started, the service is considered in progress and cannot be returned like a physical product.',
        ],
      },
      {
        title: 'Incorrect booking details',
        body: [
          'Customers are responsible for entering accurate name, date of birth, time of birth, place of birth, question, and contact details.',
          'If you notice an error before the consultation or report work begins, contact support immediately so we can try to update the booking.',
        ],
      },
      {
        title: 'Support window',
        body: [
          'For any delivery or access issue, please contact us within 48 hours of payment or booking confirmation.',
          'We will review the case and help with rescheduling, correction, or escalation where reasonably possible.',
        ],
      },
    ],
  },
  refund: {
    title: 'Refund Policy',
    eyebrow: 'Payment and cancellation',
    intro: 'This refund policy is designed for paid consultation and digital astrology services, including future payment gateway integration.',
    sections: [
      {
        title: 'Eligible refunds',
        body: [
          'A refund may be considered if payment was deducted but no booking was created, the service was not delivered due to a confirmed technical issue, or Shree Lakshmi Astro cancels the paid consultation and cannot offer a suitable replacement slot.',
          'Duplicate payments for the same booking are eligible for review and refund after payment verification.',
        ],
      },
      {
        title: 'Non-refundable cases',
        body: [
          'Payments are generally non-refundable once the astrologer has started reviewing the chart, the consultation has been completed, or a personalized report has been generated.',
          'Refunds may be declined if the customer provided incorrect birth details, missed the scheduled consultation without prior notice, or requested cancellation after work had begun.',
        ],
      },
      {
        title: 'Refund timeline',
        body: [
          'Approved refunds are initiated to the original payment method where possible.',
          'Bank, UPI, card, or payment gateway settlement timelines may vary, but approved refunds are usually processed within 7 to 10 working days after verification.',
        ],
      },
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    eyebrow: 'Customer data protection',
    intro: 'We respect the privacy of users who share personal, birth, consultation, and payment-related information with Shree Lakshmi Astro. Birth date, birth time, and birth location are treated as highly sensitive personal information.',
    sections: [
      {
        title: 'Information we collect',
        body: [
          'We may collect your name, email address, phone number, date of birth, time of birth, place of birth, consultation question, payment status, and booking history.',
          'For application security and reliability, we may also process technical information such as request identifiers, session status, device/browser data, and usage logs.',
        ],
      },
      {
        title: 'Protection of birth-related data',
        body: [
          'Birth date, exact birth time, and birth location can reveal deeply personal information. We handle this data with additional care and use it only for astrology chart generation, consultation preparation, customer support, and service records connected to your request.',
          'Sensitive birth-related data should be protected in transit through HTTPS/TLS and protected at rest using strong encryption practices such as AES-256 or equivalent controls where applicable.',
        ],
      },
      {
        title: 'How information is used',
        body: [
          'Your information is used to generate astrology charts, manage consultations, verify payments, contact you about your booking, improve service quality, and maintain platform security.',
          'We do not sell personal birth or consultation data. Access is limited to authorized team members or service providers who need it to deliver the requested service.',
        ],
      },
      {
        title: 'Anonymous and limited-use options',
        body: [
          'Where a feature does not require a full birth profile or paid consultation record, we aim to support basic or limited usage without asking for unnecessary personal details.',
          'Customers may choose not to submit optional information. Some features, such as birth-chart generation or personalized consultation, may require birth details to function correctly.',
        ],
      },
      {
        title: 'Consent and privacy rights',
        body: [
          'We follow a compliance-first approach inspired by privacy laws such as GDPR, CCPA, and other applicable data protection requirements. This includes transparent consent flows, opt-in permissions where required, and clear information about how personal data is used.',
          'Depending on your location and applicable law, you may request access, correction, deletion, restriction, or portability of your personal information, subject to legal, audit, fraud-prevention, dispute-resolution, and service-record requirements.',
        ],
      },
      {
        title: 'Payment information',
        body: [
          'When online payments are enabled, payment processing may be handled by a third-party payment gateway.',
          'Sensitive card, UPI, or banking credentials should be entered only on the secure payment gateway page. Shree Lakshmi Astro should not store full card or banking credentials in the application.',
        ],
      },
      {
        title: 'Data requests',
        body: [
          'You may contact us to request correction, access, or deletion of your personal information, subject to legal, audit, dispute-resolution, and service-record requirements.',
        ],
      },
    ],
  },
  disclaimer: {
    title: 'Disclaimer',
    eyebrow: 'Important notice',
    intro: 'Shree Lakshmi Astro provides astrology-based guidance and digital consultation support. The information shared through this platform should be used for reflection and personal decision support.',
    sections: [
      {
        title: 'No guaranteed outcome',
        body: [
          'Astrological readings, Prashna analysis, matchmaking observations, predictions, and remedies are interpretive in nature and do not guarantee any specific event, result, profit, relationship outcome, health outcome, job, visa, legal result, or financial gain.',
        ],
      },
      {
        title: 'Professional advice',
        body: [
          'Our services are not a substitute for qualified medical, legal, financial, psychological, or professional advice.',
          'For health, legal, investment, emergency, or high-risk matters, please consult an appropriately qualified professional before making decisions.',
        ],
      },
      {
        title: 'Customer responsibility',
        body: [
          'Customers are responsible for the choices they make after receiving guidance.',
          'The accuracy of any astrology interpretation depends partly on the accuracy of birth time, birth place, question context, and other details provided by the customer.',
        ],
      },
    ],
  },
};

function ContactPanel() {
  return (
    <aside className="legal-contact-panel" aria-label="Contact Shree Lakshmi Astro">
      <h2>Contact Us</h2>
      <p>For booking, payment, refund, privacy, or support queries, reach us using the official contact details below.</p>
      <a href={`mailto:${supportEmail}`} className="legal-contact-link">
        <Mail size={18} />
        <span>{supportEmail}</span>
      </a>
      {supportPhones.map((phone) => (
        <a key={phone} href={`tel:+91${phone}`} className="legal-contact-link">
          <Phone size={18} />
          <span>+91 {phone}</span>
        </a>
      ))}
    </aside>
  );
}

function PolicyNav() {
  return (
    <nav className="legal-policy-nav" aria-label="Policy pages">
      <span>Website policies</span>
      {policyLinks.map((link) => (
        <Link key={link.to} to={link.to}>{link.label}</Link>
      ))}
    </nav>
  );
}

function ContactForm() {
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get('name') || '').trim();
    const email = String(form.get('email') || '').trim();
    const phone = String(form.get('phone') || '').trim();
    const topic = String(form.get('topic') || '').trim();
    const message = String(form.get('message') || '').trim();
    const subject = encodeURIComponent(`Website enquiry: ${topic || 'Support request'}`);
    const body = encodeURIComponent([
      `Name: ${name}`,
      `Email: ${email}`,
      `Phone: ${phone || 'Not provided'}`,
      `Topic: ${topic || 'General enquiry'}`,
      '',
      'Message:',
      message,
    ].join('\n'));

    window.location.href = `mailto:${supportEmail}?subject=${subject}&body=${body}`;
  };

  return (
    <form className="contact-form" onSubmit={handleSubmit}>
      <div className="contact-form-grid">
        <label>
          <span>Full name</span>
          <input name="name" autoComplete="name" required />
        </label>
        <label>
          <span>Email address</span>
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          <span>Phone number</span>
          <input name="phone" autoComplete="tel" />
        </label>
        <label>
          <span>Support topic</span>
          <select name="topic" defaultValue="Payment or refund">
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
        <textarea
          name="message"
          rows={7}
          placeholder="Write your booking ID, payment reference, and the issue you need help with."
          required
        />
      </label>
      <button type="submit" className="contact-submit">
        <Send size={18} />
        Send Email
      </button>
      <p className="contact-form-note">
        This opens your email app with the message filled in, so you can review and send it directly to our support team.
      </p>
    </form>
  );
}

function AboutContactPage() {
  return (
    <main className="app-page legal-page">
      <section className="legal-hero">
        <div>
          <p className="legal-eyebrow">About & Contact</p>
          <h1>Shree Lakshmi Astro</h1>
          <p>
            Shree Lakshmi Astro is a digital astrology platform for Prashna Kundli, birth-chart based consultation,
            matchmaking support, and astrologer-led guidance. The application is being prepared for real-world
            paid consultation workflows with clear customer support, policy, and payment-compliance pages.
          </p>
        </div>
      </section>

      <section className="legal-document-layout">
        <PolicyNav />
        <div className="legal-document">
          <section className="legal-section">
            <h2>What we provide</h2>
            <p>
              We help customers submit birth details, consultation questions, Prashna details, and matchmaking
              information so the astrologer can review the case with better context and maintain service history.
            </p>
          </section>
          <section className="legal-section">
            <h2>Customer support</h2>
            <p>
              Please include your name, registered phone number, email address, booking ID or payment reference,
              and a short description of the issue when contacting support.
            </p>
          </section>
          <section className="legal-section legal-section--contact">
            <div>
              <h2>Send us a message</h2>
              <p>
                Use this form for booking, payment, refund, privacy, or consultation support. It prepares an email
                with your details so the support team receives a clear request.
              </p>
            </div>
            <ContactForm />
          </section>
          <ContactPanel />
        </div>
      </section>
    </main>
  );
}

const LegalPage: React.FC<{ kind: LegalPageKind }> = ({ kind }) => {
  if (kind === 'about-contact') return <AboutContactPage />;

  const page = pageCopy[kind];

  return (
    <main className="app-page legal-page">
      <section className="legal-hero">
        <div>
          <p className="legal-eyebrow">{page.eyebrow}</p>
          <h1>{page.title}</h1>
          <p>{page.intro}</p>
          <p className="legal-updated">Last updated: July 13, 2026</p>
        </div>
      </section>

      <section className="legal-document-layout">
        <PolicyNav />
        <div className="legal-document">
          {page.sections.map((section) => (
            <section className="legal-section" key={section.title}>
              <h2>{section.title}</h2>
              {section.body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </section>
          ))}
          <ContactPanel />
        </div>
      </section>
    </main>
  );
};

export default LegalPage;
