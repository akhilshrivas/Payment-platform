import apiClient from './client';
import type { ApiResponse, Wallet, TransferRequest } from '../types';
import type { Transaction } from '../types/transaction';

export const walletApi = {
  getWallet: () =>
    apiClient.get<ApiResponse<Wallet>>('/wallet/'),

  getBalance: () =>
    apiClient.get<ApiResponse<Pick<Wallet, 'currency' | 'balance' | 'available_balance'>>>('/wallet/balance/'),

  transfer: (data: TransferRequest) =>
    apiClient.post<ApiResponse<Transaction>>('/wallet/transfer/', data),
};
