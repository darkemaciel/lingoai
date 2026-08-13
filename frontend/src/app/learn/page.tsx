'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import GamificationFeedback from '@/components/GamificationFeedback';
import type { ActivityAnswerResponse, NextActivityResponse } from '@/services/types';

export default function LearnPage() {
  const [activity, setActivity] = useState<NextActivityResponse | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [result, setResult] = useState<ActivityAnswerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNextActivity = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setAnswerText('');
    try {
      const res = await fetch('/api/activities/next');
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error?.message ?? 'Could not load the next activity');
      }
      setActivity(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNextActivity();
  }, [loadNextActivity]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!activity || !answerText.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/activities/${activity.activity_id}/answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_submission_id: crypto.randomUUID(),
          response: { text: answerText },
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error?.message ?? 'Could not submit your answer');
      }
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  }

  const instructions =
    typeof activity?.prompt_content?.instructions === 'string'
      ? (activity.prompt_content.instructions as string)
      : null;

  return (
    <main>
      <h1>Prática</h1>
      <nav>
        <Link href="/learn/conversation">Ir para conversa</Link> ·{' '}
        <Link href="/progress">Ver progresso</Link>
      </nav>

      {loading && <p>Carregando atividade…</p>}
      {error && <p role="alert">{error}</p>}

      {activity && !loading && (
        <>
          <p>
            <strong>Habilidade:</strong> {activity.skill} · <strong>Tipo:</strong> {activity.type}
          </p>
          {instructions && <p>{instructions}</p>}

          {!result && (
            <form onSubmit={handleSubmit}>
              <textarea
                aria-label="Sua resposta"
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                disabled={submitting}
                rows={4}
              />
              <div>
                <button type="submit" disabled={submitting || !answerText.trim()}>
                  {submitting ? 'Enviando…' : 'Enviar resposta'}
                </button>
              </div>
            </form>
          )}

          {result && (
            <section>
              <p>{result.correct ? '✅ Correto!' : '💬 Quase lá!'}</p>
              <p>{result.feedback_text}</p>
              {result.level_advanced && <p>🎉 Você avançou de nível em {activity.skill}!</p>}
              <GamificationFeedback delta={result.gamification_delta} />
              <button type="button" onClick={loadNextActivity}>
                Próxima atividade
              </button>
            </section>
          )}
        </>
      )}
    </main>
  );
}
