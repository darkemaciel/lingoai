'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const registerRes = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!registerRes.ok) {
        const data = await registerRes.json();
        throw new Error(data.error?.message ?? 'Registration failed');
      }

      // FR-2: registration auto-starts placement, so log the new user in
      // immediately and kick off their placement session.
      const loginRes = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!loginRes.ok) {
        const data = await loginRes.json();
        throw new Error(data.error?.message ?? 'Login after registration failed');
      }

      const sessionRes = await fetch('/api/placement/sessions', { method: 'POST' });
      if (!sessionRes.ok) {
        const data = await sessionRes.json();
        throw new Error(data.error?.message ?? 'Could not start placement session');
      }
      const session = await sessionRes.json();
      router.push(`/placement?sessionId=${session.placement_session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Crie sua conta</h1>
      <p>Vamos começar com uma breve conversa para descobrir seu nível.</p>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">E-mail</label>
          <br />
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="password">Senha</label>
          <br />
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Criando conta…' : 'Criar conta e começar'}
        </button>
      </form>
    </main>
  );
}
