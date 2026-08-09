import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { walletApi } from '../../api/wallet';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { ArrowRightLeft } from 'lucide-react';

export default function Transfer() {
  const navigate = useNavigate();
  const [receiverEmail, setReceiverEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (parseFloat(amount) <= 0) {
      setFieldErrors({ amount: 'Amount must be greater than 0' });
      return;
    }

    setIsLoading(true);

    try {
      await walletApi.transfer({
        receiver_email: receiverEmail,
        amount,
        description
      });
      // Navigate to transactions on success
      navigate('/transactions', { state: { message: 'Transfer successful!' } });
    } catch (err: any) {
      if (err.response?.data?.errors && Object.keys(err.response.data.errors).length > 0) {
        const errors = err.response.data.errors;
        const formattedErrors: Record<string, string> = {};
        Object.keys(errors).forEach(key => {
          formattedErrors[key] = Array.isArray(errors[key]) ? errors[key][0] : errors[key];
        });
        setFieldErrors(formattedErrors);
      } else {
        setError(err.response?.data?.message || 'Transfer failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center">
          <ArrowRightLeft className="mr-3 h-6 w-6 text-indigo-600" />
          Send Money
        </h1>
      </div>

      <div className="bg-white shadow rounded-2xl overflow-hidden border border-gray-100 p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm font-medium">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <Input
              label="Recipient Email"
              name="receiverEmail"
              type="email"
              required
              placeholder="friend@example.com"
              value={receiverEmail}
              onChange={(e) => setReceiverEmail(e.target.value)}
              error={fieldErrors.receiver_email}
            />

            <Input
              label="Amount (₹)"
              name="amount"
              type="number"
              step="0.01"
              min="0.01"
              required
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              error={fieldErrors.amount}
            />

            <Input
              label="Description (Optional)"
              name="description"
              type="text"
              placeholder="Dinner, Rent, etc."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              error={fieldErrors.description}
            />
          </div>

          <div className="pt-4">
            <Button
              type="submit"
              className="w-full"
              size="lg"
              isLoading={isLoading}
            >
              Send Securely
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
