import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '../types';
import type {
  Payment,
  CreateOrderRequest,
  CreateOrderResponse,
  VerifyPaymentRequest,
} from '../types/payment';

export const paymentsApi = {
  createOrder: (data: CreateOrderRequest) =>
    apiClient.post<ApiResponse<CreateOrderResponse>>('/payments/create-order/', data),

  verifyPayment: (data: VerifyPaymentRequest) =>
    apiClient.post<ApiResponse<Payment>>('/payments/verify/', data),

  getPayments: (page = 1) =>
    apiClient.get<PaginatedResponse<Payment>>('/payments/', { params: { page } }),

  getPayment: (id: string) =>
    apiClient.get<ApiResponse<Payment>>(`/payments/${id}/`),

  refundPayment: (id: string, amount?: string) =>
    apiClient.post<ApiResponse>(`/payments/${id}/refund/`, amount ? { amount } : {}),
};
