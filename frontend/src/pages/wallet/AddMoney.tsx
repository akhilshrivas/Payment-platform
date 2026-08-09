import React, { useState, useEffect } from 'react';
import { Wallet as WalletIcon, ShieldCheck, ArrowRight, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { paymentsApi } from '../../api/payments';
import { walletApi } from '../../api/wallet';
import type { Wallet } from '../../types/wallet';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

interface RazorpayResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export const AddMoney: React.FC = () => {
  const [amount, setAmount] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchWallet = async () => {
      try {
        const res = await walletApi.getWallet();
        if (res.data.success && res.data.data) {
          setWallet(res.data.data);
        }
      } catch (err) {
        console.error('Failed to fetch wallet:', err);
      }
    };
    fetchWallet();
  }, []);

  const loadRazorpayScript = (): Promise<boolean> => {
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const value = parseFloat(amount);
    if (isNaN(value) || value < 1) {
      setError('Please enter a valid amount (minimum ₹1)');
      return;
    }

    setLoading(true);

    try {
      const resLoaded = await loadRazorpayScript();
      if (!resLoaded) {
        throw new Error('Razorpay SDK failed to load. Are you offline?');
      }

      // 1. Create order on backend
      const { data } = await paymentsApi.createOrder({ amount: value.toString(), description: 'Wallet Deposit' });
      
      if (!data.success || !data.data) {
        throw new Error(data.message || 'Failed to create payment order');
      }

      const checkoutData = data.data;

      // 2. Initialize Razorpay Checkout
      const options = {
        key: checkoutData.razorpay_key_id,
        amount: checkoutData.amount, // in paise
        currency: checkoutData.currency,
        name: 'PayPlatform',
        description: checkoutData.description,
        order_id: checkoutData.razorpay_order_id,
        prefill: {
          name: `${user?.first_name} ${user?.last_name}`,
          email: user?.email,
        },
        theme: {
          color: '#4f46e5',
        },
        handler: async function (response: RazorpayResponse) {
          try {
            setLoading(true);
            // 3. Verify payment signature on backend
            const verifyRes = await paymentsApi.verifyPayment({
              payment_id: checkoutData.payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });

            if (verifyRes.data.success) {
              navigate('/dashboard', { state: { message: 'Money added successfully!' } });
            } else {
              setError(verifyRes.data.message || 'Payment verification failed');
            }
          } catch (err: any) {
            setError(err.response?.data?.message || 'Payment verification failed');
          } finally {
            setLoading(false);
          }
        },
      };

      const rzp = new (window as any).Razorpay(options);
      
      rzp.on('payment.failed', function (response: any) {
        setError(`Payment Failed: ${response.error.description}`);
        setLoading(false);
      });

      rzp.open();
    } catch (err: any) {
      setError(err.message || err.response?.data?.message || 'Something went wrong');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center space-x-3">
        <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl">
          <WalletIcon className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Add Money</h1>
          <p className="text-gray-500 dark:text-gray-400">Deposit funds directly into your wallet securely.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
        <div className="p-6 md:p-8">
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Current Balance</h2>
            <div className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">
              ₹{parseFloat(wallet?.balance || '0').toFixed(2)}
            </div>
          </div>

          <form onSubmit={handleDeposit} className="space-y-6">
            <div>
              <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Deposit Amount (INR)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-xl">₹</span>
                </div>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="pl-8 text-lg py-3"
                  placeholder="0.00"
                  required
                />
              </div>
              <div className="mt-3 flex gap-2">
                {[500, 1000, 2000, 5000].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setAmount(preset.toString())}
                    className="px-3 py-1 text-sm border border-gray-200 dark:border-slate-700 rounded-full text-gray-600 dark:text-gray-400 hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                  >
                    +₹{preset}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-lg bg-red-50 text-red-600 border border-red-100 dark:bg-red-900/20 dark:border-red-900/50 text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-12 text-lg group"
              disabled={loading || !amount || parseFloat(amount) < 1}
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
              ) : (
                <span className="flex items-center justify-center">
                  Proceed to Pay
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                </span>
              )}
            </Button>
          </form>
        </div>
        
        <div className="bg-gray-50 dark:bg-slate-800/50 px-6 py-4 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
          <ShieldCheck className="h-5 w-5 mr-2 text-green-500" />
          Secured by Razorpay. 100% safe payments.
        </div>
      </div>
    </div>
  );
};

export default AddMoney;
