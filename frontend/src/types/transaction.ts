export type TransactionType = 'DEPOSIT' | 'WITHDRAWAL' | 'TRANSFER' | 'PAYMENT' | 'REFUND';
export type TransactionStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'REFUNDED';

export interface Transaction {
  id: string;
  transaction_reference: string;
  sender_email: string | null;
  receiver_email: string | null;
  amount: string;
  signed_amount: string; // e.g. "+100.00" or "-50.00"
  currency: string;
  transaction_type: TransactionType;
  status: TransactionStatus;
  description: string;
  razorpay_payment_id: string | null;
  created_at: string;
  updated_at: string;
}
