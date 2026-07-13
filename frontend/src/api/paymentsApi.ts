import { apiClient } from './client';

export interface RazorpayOrderRequest {
  amount_inr?: number;
  currency?: 'INR';
  receipt?: string;
  purpose?: string;
  consultation_case_id?: string;
  match_request_id?: string;
}

export interface RazorpayVerifyRequest {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export const paymentsApi = {
  createRazorpayOrder: async (payload: RazorpayOrderRequest = {}) => {
    const response = await apiClient.post('/api/payments/razorpay/order', payload);
    return response.data;
  },

  verifyRazorpayPayment: async (payload: RazorpayVerifyRequest) => {
    const response = await apiClient.post('/api/payments/razorpay/verify', payload);
    return response.data;
  },
};
