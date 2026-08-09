import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Wallet as WalletIcon, ArrowUpRight, ArrowDownRight, Loader2 } from 'lucide-react';
import { walletApi } from '../../api/wallet';
import { transactionsApi } from '../../api/transactions';
import type { Wallet } from '../../types/wallet';
import type { Transaction } from '../../types/transaction';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const { user } = useAuth();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [walletRes, txRes] = await Promise.all([
          walletApi.getWallet(),
          transactionsApi.getTransactions({ page: 1 })
        ]);
        
        if (walletRes.data.success && walletRes.data.data) {
          setWallet(walletRes.data.data);
        }
        
        if (txRes.data.success && txRes.data.data) {
          setRecentTransactions(txRes.data.data.slice(0, 5)); // Just take top 5 for dashboard
        }
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">
          Welcome back, {user?.first_name}!
        </h1>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Wallet Balance Card */}
        <div className="overflow-hidden rounded-2xl bg-indigo-600 shadow text-white p-6 relative lg:col-span-1">
          <div className="absolute right-0 top-0 -mr-8 -mt-8 opacity-10">
            <WalletIcon className="w-32 h-32" />
          </div>
          <p className="text-sm font-medium text-indigo-100 mb-1">Available Balance</p>
          <p className="text-4xl font-bold tracking-tight">₹{wallet?.available_balance || '0.00'}</p>
          <div className="mt-4 flex items-center space-x-2 text-sm text-indigo-200">
            <span>•••• •••• •••• {wallet?.id.slice(-4)}</span>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="overflow-hidden rounded-2xl bg-white shadow p-6 border border-gray-100 lg:col-span-2">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-4">
            <Link
              to="/transfer"
              className="flex items-center p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="bg-indigo-100 text-indigo-600 p-3 rounded-lg mr-4">
                <ArrowUpRight className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">Send Money</p>
                <p className="text-sm text-gray-500">Transfer to anyone</p>
              </div>
            </Link>
            <Link
              to="/deposit"
              className="flex items-center p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="bg-green-100 text-green-600 p-3 rounded-lg mr-4">
                <ArrowDownRight className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">Add Money</p>
                <p className="text-sm text-gray-500">Deposit to wallet</p>
              </div>
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="bg-white shadow rounded-2xl overflow-hidden border border-gray-100">
        <div className="px-6 py-5 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-medium leading-6 text-gray-900">Recent Transactions</h3>
          <Link to="/transactions" className="text-sm text-indigo-600 hover:text-indigo-900 font-medium">
            View all
          </Link>
        </div>
        <div className="divide-y divide-gray-200">
          {recentTransactions.length === 0 ? (
            <div className="p-6 text-center text-gray-500">No transactions found.</div>
          ) : (
            recentTransactions.map((tx) => (
              <div key={tx.id} className="p-6 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div className="flex items-center">
                  <div className={`p-2 rounded-full mr-4 ${
                    tx.signed_amount.startsWith('-') ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'
                  }`}>
                    {tx.signed_amount.startsWith('-') ? <ArrowUpRight className="h-5 w-5" /> : <ArrowDownRight className="h-5 w-5" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{tx.description || tx.transaction_type}</p>
                    <p className="text-xs text-gray-500">{new Date(tx.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <div className={`text-sm font-semibold ${
                  tx.signed_amount.startsWith('-') ? 'text-gray-900' : 'text-green-600'
                }`}>
                  {tx.signed_amount.startsWith('-') ? '' : '+'}₹{tx.amount}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
