import { useState } from 'react';
import { Link } from 'react-router-dom';

const LoginRegister = () => {
  const [tab, setTab] = useState<'login' | 'register'>('login');

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-8">
      <div className="w-full max-w-xl rounded-2xl bg-white shadow-xl">
        <div className="flex border-b border-slate-200">
          <button
            type="button"
            className={`flex-1 px-6 py-4 text-lg font-semibold transition-colors ${tab === 'login' ? 'text-slate-900 border-b-2 border-orange-400' : 'text-slate-400'}`}
            onClick={() => setTab('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={`flex-1 px-6 py-4 text-lg font-semibold transition-colors ${tab === 'register' ? 'text-slate-900 border-b-2 border-orange-400' : 'text-slate-400'}`}
            onClick={() => setTab('register')}
          >
            Register
          </button>
        </div>
        <div className="p-6">
          {tab === 'login' ? (
            <p className="text-slate-500">
              Login form coming soon. For now, request access from the{' '}
              <Link to="/" className="text-orange-500">team</Link>.
            </p>
          ) : (
            <p className="text-slate-500">
              Registration workflow will be implemented in the next phase.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginRegister;
