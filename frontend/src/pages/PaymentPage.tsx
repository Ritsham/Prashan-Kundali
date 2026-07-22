import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, CreditCard, Loader2, ShieldCheck } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { paymentsApi } from '../api/paymentsApi';

type CheckoutResponse = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

type RazorpayCheckout = {
  open: () => void;
  on: (event: 'payment.failed', handler: (response: { error?: { description?: string } }) => void) => void;
};

type RazorpayConstructor = new (options: Record<string, unknown>) => RazorpayCheckout;

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

function loadRazorpayCheckout(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve();
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
    );
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('Could not load Razorpay Checkout.')), {
        once: true,
      });
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Could not load Razorpay Checkout.'));
    document.head.appendChild(script);
  });
}

function queryValue(params: URLSearchParams, names: string[]): string {
  for (const name of names) {
    const value = params.get(name)?.trim();
    if (value) return value;
  }
  return '';
}

export default function PaymentPage() {
  const [searchParams] = useSearchParams();
  const initialCaseId = useMemo(
    () => queryValue(searchParams, ['caseId', 'consultation_case_id', 'consultationCaseId']),
    [searchParams],
  );
  const initialEmail = useMemo(() => queryValue(searchParams, ['email', 'requester_email']), [searchParams]);
  const [caseId, setCaseId] = useState(initialCaseId);
  const [email, setEmail] = useState(initialEmail);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<null | { orderId: string; paymentId: string }>(null);

  const startPayment = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setSuccess(null);

    try {
      await loadRazorpayCheckout();
      const Razorpay = window.Razorpay;
      if (!Razorpay) {
        throw new Error('Razorpay Checkout is unavailable. Please refresh and try again.');
      }

      const orderResponse = await paymentsApi.createRazorpayOrder({
        currency: 'INR',
        consultation_case_id: caseId,
        requester_email: email || undefined,
        purpose: 'consultation',
      });

      const checkoutResult = await new Promise<CheckoutResponse>((resolve, reject) => {
        const checkout = new Razorpay({
          key: orderResponse.key_id,
          amount: orderResponse.order.amount,
          currency: orderResponse.order.currency,
          name: 'Shree Lakshmi Astro',
          description: 'Astrology consultation',
          order_id: orderResponse.order.id,
          prefill: {
            name,
            email,
            contact: phone,
          },
          notes: {
            consultation_case_id: caseId,
          },
          theme: {
            color: '#8c3d25',
          },
          modal: {
            ondismiss: () => reject(new Error('Payment was closed before completion.')),
          },
          handler: resolve,
        });
        checkout.on('payment.failed', (response) => {
          reject(new Error(response.error?.description || 'Payment failed. Please try again.'));
        });
        checkout.open();
      });

      await paymentsApi.verifyRazorpayPayment(checkoutResult);
      setSuccess({
        orderId: checkoutResult.razorpay_order_id,
        paymentId: checkoutResult.razorpay_payment_id,
      });
    } catch (paymentError: any) {
      setError(paymentError?.message || 'Could not complete payment.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="payment-page" aria-labelledby="payment-title">
      <section className="payment-hero">
        <div>
          <p className="payment-eyebrow">Secure Razorpay checkout</p>
          <h1 id="payment-title">Complete consultation payment</h1>
          <p>
            Pay securely with UPI, cards, netbanking, or wallet. Your payment is verified on the server before the
            consultation is marked paid.
          </p>
        </div>
        <div className="payment-trust-strip" aria-label="Payment safeguards">
          <span>
            <ShieldCheck size={18} />
            Server verified
          </span>
          <span>
            <CreditCard size={18} />
            Razorpay Checkout
          </span>
        </div>
      </section>

      <section className="payment-layout">
        <form className="payment-panel" onSubmit={startPayment}>
          <label>
            <span>Consultation case ID</span>
            <input
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
              placeholder="case_..."
              required
            />
          </label>
          <label>
            <span>Email used for booking</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>
          <label>
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Full name" />
          </label>
          <label>
            <span>Phone</span>
            <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+91..." />
          </label>

          {error && <div className="payment-alert payment-alert--error">{error}</div>}
          {success && (
            <div className="payment-alert payment-alert--success">
              <CheckCircle2 size={18} />
              Payment verified. Payment ID: {success.paymentId}
            </div>
          )}

          <button type="submit" className="payment-submit" disabled={busy}>
            {busy ? <Loader2 className="payment-spinner" size={18} /> : <CreditCard size={18} />}
            {busy ? 'Processing...' : 'Pay with Razorpay'}
          </button>
        </form>

        <aside className="payment-summary" aria-label="Payment summary">
          <h2>What happens next</h2>
          <p>Once Razorpay confirms the payment, this case is marked paid and becomes ready for appointment scheduling.</p>
          <dl>
            <div>
              <dt>Provider</dt>
              <dd>Razorpay</dd>
            </div>
            <div>
              <dt>Currency</dt>
              <dd>INR</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{success ? 'Paid' : 'Pending payment'}</dd>
            </div>
          </dl>
        </aside>
      </section>
    </main>
  );
}
