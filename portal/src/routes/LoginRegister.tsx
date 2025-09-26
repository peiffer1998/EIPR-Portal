import type { FormEvent } from 'react';
import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { login, registerOwner } from '../lib/auth';
import { fetchPortalMe } from '../lib/portal';
import { useAuth } from '../state/AuthContext';
import { PORTAL_ME_QUERY_KEY } from '../lib/usePortalMe';

const reservationAccountSlug = import.meta.env.VITE_PORTAL_ACCOUNT_SLUG;

const LoginRegister = () => {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    phoneNumber: '',
  });
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setSession } = useAuth();

  const accountSlugHint = useMemo(() => reservationAccountSlug ?? 'Your resort slug', []);

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async (token) => {
      const me = await fetchPortalMe();
      const owner = me.owner
        ? {
            id: me.owner.id,
            firstName: me.owner.user.first_name,
            lastName: me.owner.user.last_name,
            email: me.owner.user.email,
          }
        : undefined;
      setSession(token, owner);
      queryClient.setQueryData(PORTAL_ME_QUERY_KEY, me);
      navigate('/', { replace: true });
    },
    onError: () => {
      setError('Unable to sign in with the provided credentials.');
    },
  });

  const registerMutation = useMutation({
    mutationFn: registerOwner,
    onSuccess: async ({ token, owner }) => {
      setSession(token, owner);
      const me = await fetchPortalMe();
      queryClient.setQueryData(PORTAL_ME_QUERY_KEY, me);
      navigate('/', { replace: true });
    },
    onError: () => {
      setError('Unable to register with those details. Please try again.');
    },
  });

  const handleLoginSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    loginMutation.mutate({ ...loginForm });
  };

  const handleRegisterSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    registerMutation.mutate({
      firstName: registerForm.firstName,
      lastName: registerForm.lastName,
      email: registerForm.email,
      password: registerForm.password,
      phoneNumber: registerForm.phoneNumber || undefined,
      accountSlug: reservationAccountSlug,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-xl">
        <div className="flex border-b border-slate-200">
          <button
            type="button"
            className={`flex-1 px-6 py-4 text-lg font-semibold transition ${tab === 'login' ? 'text-slate-900 border-b-2 border-orange-500' : 'text-slate-400 hover:text-slate-600'}`}
            onClick={() => {
              setTab('login');
              setError(null);
            }}
          >
            Login
          </button>
          <button
            type="button"
            className={`flex-1 px-6 py-4 text-lg font-semibold transition ${tab === 'register' ? 'text-slate-900 border-b-2 border-orange-500' : 'text-slate-400 hover:text-slate-600'}`}
            onClick={() => {
              setTab('register');
              setError(null);
            }}
          >
            Register
          </button>
        </div>
        <div className="p-8">
          {error && <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
          {tab === 'login' ? (
            <form className="space-y-4" onSubmit={handleLoginSubmit}>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="login-email">
                  Email
                </label>
                <input
                  id="login-email"
                  type="email"
                  required
                  value={loginForm.email}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, email: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="login-password">
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  required
                  value={loginForm.password}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                className="w-full rounded-lg bg-orange-500 px-4 py-2 font-semibold text-white transition hover:bg-orange-600"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleRegisterSubmit}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-firstName">
                    First name
                  </label>
                  <input
                    id="register-firstName"
                    required
                    value={registerForm.firstName}
                    onChange={(event) => setRegisterForm((prev) => ({ ...prev, firstName: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-lastName">
                    Last name
                  </label>
                  <input
                    id="register-lastName"
                    required
                    value={registerForm.lastName}
                    onChange={(event) => setRegisterForm((prev) => ({ ...prev, lastName: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-email">
                  Email
                </label>
                <input
                  id="register-email"
                  type="email"
                  required
                  value={registerForm.email}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, email: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-phone">
                  Mobile phone
                </label>
                <input
                  id="register-phone"
                  value={registerForm.phoneNumber}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, phoneNumber: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="register-password">
                  Password
                </label>
                <input
                  id="register-password"
                  type="password"
                  minLength={8}
                  required
                  value={registerForm.password}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, password: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:border-orange-500 focus:outline-none"
                />
                <p className="mt-1 text-xs text-slate-400">Our local resort slug is {accountSlugHint}.</p>
              </div>
              <button
                type="submit"
                className="w-full rounded-lg bg-orange-500 px-4 py-2 font-semibold text-white transition hover:bg-orange-600"
                disabled={registerMutation.isPending}
              >
                {registerMutation.isPending ? 'Creating account…' : 'Create account'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginRegister;
