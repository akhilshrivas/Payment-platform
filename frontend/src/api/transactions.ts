import apiClient from './client';
import type { PaginatedResponse } from '../types';
import type { Transaction } from '../types/transaction';

export const transactionsApi = {
  getTransactions: (params?: {
    page?: number;
    type?: string;
    status?: string;
    search?: string;
    date_from?: string;
    date_to?: string;
  }) =>
    apiClient.get<PaginatedResponse<Transaction>>('/transactions/', { params }),

  getTransaction: (id: string) =>
    apiClient.get<{ success: boolean; data: Transaction }>(`/transactions/${id}/`),
};
