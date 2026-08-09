export type RecurringFrequency = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';
export type RecurringStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED' | 'FAILED';

export interface RecurringPayment {
  id: string;
  user_email: string;
  receiver_email: string;
  amount: string;
  currency: string;
  frequency: RecurringFrequency;
  start_date: string;
  end_date: string | null;
  next_payment_date: string;
  last_payment_date: string | null;
  status: RecurringStatus;
  description: string;
  failure_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateRecurringPaymentRequest {
  receiver_email: string;
  amount: string;
  currency?: string;
  frequency: RecurringFrequency;
  start_date: string;
  end_date?: string;
  description?: string;
}
