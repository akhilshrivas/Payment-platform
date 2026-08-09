import React, { useEffect, useState } from 'react';
import { Repeat, Plus, Loader2, PauseCircle, PlayCircle, XCircle } from 'lucide-react';
import { recurringApi } from '../../api/recurring';
import type { RecurringPayment } from '../../types/recurring';
import { Button } from '../../components/ui/Button';

export const RecurringPayments: React.FC = () => {
  const [payments, setPayments] = useState<RecurringPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const res = await recurringApi.getRecurringPayments();
      if (res.data.success && res.data.data) {
        setPayments(res.data.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load recurring payments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, []);

  const handlePause = async (id: string) => {
    try {
      await recurringApi.pauseRecurringPayment(id);
      fetchPayments();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to pause');
    }
  };

  const handleResume = async (id: string) => {
    try {
      await recurringApi.resumeRecurringPayment(id);
      fetchPayments();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to resume');
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm('Are you sure you want to cancel this recurring payment?')) return;
    try {
      await recurringApi.cancelRecurringPayment(id);
      fetchPayments();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to cancel');
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Recurring Payments</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage your automatic transfers and subscriptions.</p>
        </div>
        <Button className="flex items-center" onClick={() => alert('New Recurring UI coming in Phase 6')}>
          <Plus className="h-5 w-5 mr-2" />
          New Schedule
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 rounded-lg">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 text-indigo-600 animate-spin" />
        </div>
      ) : payments.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-900 rounded-2xl shadow border border-gray-100 dark:border-slate-800">
          <Repeat className="h-12 w-12 text-gray-400 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">No active schedules</h3>
          <p className="text-gray-500 dark:text-gray-400 mt-2">You haven't set up any recurring payments yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {payments.map((rp) => (
            <div key={rp.id} className="bg-white dark:bg-slate-900 rounded-2xl shadow-lg border border-gray-100 dark:border-slate-800 p-6 flex flex-col relative overflow-hidden">
              <div className={`absolute top-0 right-0 p-4 opacity-10 ${rp.status === 'ACTIVE' ? 'text-indigo-600' : 'text-gray-400'}`}>
                <Repeat className="h-24 w-24 -mr-8 -mt-8" />
              </div>
              
              <div className="flex items-center justify-between mb-4 relative z-10">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  rp.status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                  rp.status === 'PAUSED' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {rp.status}
                </span>
                <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-md font-mono">
                  {rp.frequency}
                </span>
              </div>

              <div className="mb-6 relative z-10">
                <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                  ₹{rp.amount}
                </p>
                <p className="text-sm text-gray-500 font-medium">To: {rp.receiver_email}</p>
                {rp.description && (
                  <p className="text-sm text-gray-400 mt-1 italic">"{rp.description}"</p>
                )}
              </div>

              <div className="space-y-2 mb-6 bg-gray-50 dark:bg-slate-800/50 p-4 rounded-xl text-sm relative z-10">
                <div className="flex justify-between">
                  <span className="text-gray-500">Next Payment:</span>
                  <span className="font-medium text-gray-900">{rp.next_payment_date}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Last Payment:</span>
                  <span className="text-gray-900">{rp.last_payment_date || 'N/A'}</span>
                </div>
              </div>

              <div className="mt-auto grid grid-cols-2 gap-3 relative z-10">
                {rp.status === 'ACTIVE' && (
                  <Button variant="outline" onClick={() => handlePause(rp.id)} className="w-full flex items-center justify-center">
                    <PauseCircle className="h-4 w-4 mr-2" /> Pause
                  </Button>
                )}
                {rp.status === 'PAUSED' && (
                  <Button variant="outline" onClick={() => handleResume(rp.id)} className="w-full flex items-center justify-center border-indigo-200 text-indigo-700">
                    <PlayCircle className="h-4 w-4 mr-2" /> Resume
                  </Button>
                )}
                {rp.status !== 'CANCELLED' && rp.status !== 'COMPLETED' && (
                  <Button variant="danger" onClick={() => handleCancel(rp.id)} className="w-full flex items-center justify-center">
                    <XCircle className="h-4 w-4 mr-2" /> Cancel
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecurringPayments;
