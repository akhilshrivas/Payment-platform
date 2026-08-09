import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '../types';
import type { RecurringPayment, CreateRecurringPaymentRequest } from '../types/recurring';

export const recurringApi = {
  getRecurringPayments: (params?: { page?: number; status?: string }) =>
    apiClient.get<PaginatedResponse<RecurringPayment>>('/recurring-payments/', { params }),

  createRecurringPayment: (data: CreateRecurringPaymentRequest) =>
    apiClient.post<ApiResponse<RecurringPayment>>('/recurring-payments/', data),

  getRecurringPayment: (id: string) =>
    apiClient.get<ApiResponse<RecurringPayment>>(`/recurring-payments/${id}/`),

  updateRecurringPayment: (id: string, data: Partial<{ amount: string; description: string; end_date: string }>) =>
    apiClient.patch<ApiResponse<RecurringPayment>>(`/recurring-payments/${id}/`, data),

  cancelRecurringPayment: (id: string) =>
    apiClient.delete<ApiResponse>(`/recurring-payments/${id}/`),

  pauseRecurringPayment: (id: string) =>
    apiClient.post<ApiResponse<RecurringPayment>>(`/recurring-payments/${id}/pause/`),

  resumeRecurringPayment: (id: string) =>
    apiClient.post<ApiResponse<RecurringPayment>>(`/recurring-payments/${id}/resume/`),
};
