import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Wallet } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone_number: '',
    password: '',
    confirm_password: '',
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    // Clear field error when typing
    if (fieldErrors[e.target.name]) {
      setFieldErrors(prev => ({ ...prev, [e.target.name]: '' }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (formData.password !== formData.confirm_password) {
      setFieldErrors({ confirm_password: 'Passwords do not match' });
      return;
    }

    setIsLoading(true);

    try {
      await register(formData);
      // Auto redirect to login on success
      navigate('/login', { state: { message: 'Account created successfully. Please sign in.' } });
    } catch (err: any) {
      if (err.response?.data?.errors) {
        // Backend validation errors mapping
        const errors = err.response.data.errors;
        const formattedErrors: Record<string, string> = {};
        Object.keys(errors).forEach(key => {
          formattedErrors[key] = Array.isArray(errors[key]) ? errors[key][0] : errors[key];
        });
        setFieldErrors(formattedErrors);
      } else {
        const msg = err.response?.data?.message || 'Failed to register. Please try again later.';
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-xl w-full space-y-8 bg-white p-10 rounded-2xl shadow-xl">
        <div className="flex flex-col items-center">
          <div className="h-12 w-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-4">
            <Wallet className="h-6 w-6" />
          </div>
          <h2 className="text-center text-3xl font-extrabold text-gray-900">Create your account</h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
              Sign in
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 text-red-500 p-3 rounded-md text-sm text-center">
              {error}
            </div>
          )}
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="First name"
              name="first_name"
              required
              value={formData.first_name}
              onChange={handleChange}
              error={fieldErrors.first_name}
            />
            <Input
              label="Last name"
              name="last_name"
              required
              value={formData.last_name}
              onChange={handleChange}
              error={fieldErrors.last_name}
            />
          </div>

          <div className="space-y-4">
            <Input
              label="Email address"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              error={fieldErrors.email}
            />
            
            <Input
              label="Phone number (optional)"
              name="phone_number"
              type="tel"
              value={formData.phone_number}
              onChange={handleChange}
              error={fieldErrors.phone_number}
              placeholder="+91..."
            />
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                error={fieldErrors.password}
              />
              <Input
                label="Confirm Password"
                name="confirm_password"
                type="password"
                required
                value={formData.confirm_password}
                onChange={handleChange}
                error={fieldErrors.confirm_password}
              />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isLoading}
          >
            Create account
          </Button>
        </form>
      </div>
    </div>
  );
}
