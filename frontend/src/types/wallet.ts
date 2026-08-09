export interface Wallet {
  id: string;
  owner_email: string;
  currency: string;
  balance: string;
  available_balance: string;
  created_at: string;
  updated_at: string;
}

export interface TransferRequest {
  receiver_email: string;
  amount: string;
  description?: string;
}
