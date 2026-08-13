'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

interface Turn {
  speaker: 'agent' | 'student';
  text: string;
}

function PlacementConversation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('sessionId');

  const [turns, setTurns] = useState<Turn[]>([
    {
      speaker: 'agent',
      text: 'Olá! Vamos começar sua conversa de nivelamento. Escreva uma resposta para iniciarmos — conte um pouco sobre você.',
    },
  ]);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) {
      router.replace('/register');
    }
  }, [sessionId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!sessionId || !answer.trim()) return;
    setError(null);
    setSubmitting(true);
    const studentText = answer;
    setTurns((prev) => [...prev, { speaker: 'student', text: studentText }]);
    setAnswer('');

    try {
      const res = await fetch(`/api/placement/sessions/${sessionId}/answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_submission_id: crypto.randomUUID(),
          content_text: studentText,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error?.message ?? 'Could not submit answer');
      }
      const data = await res.json();
      if (data.next_prompt) {
        setTurns((prev) => [...prev, { speaker: 'agent', text: data.next_prompt.content_text }]);
      }
      if (data.session_status === 'completed' || data.next_prompt === null) {
        setFinished(true);
        router.push(`/placement/result?sessionId=${sessionId}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Conversa de nivelamento</h1>
      <div aria-live="polite">
        {turns.map((turn, index) => (
          <p key={index}>
            <strong>{turn.speaker === 'agent' ? 'IA' : 'Você'}:</strong> {turn.text}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>
      {error && <p role="alert">{error}</p>}
      {!finished && (
        <form onSubmit={handleSubmit}>
          <textarea
            aria-label="Sua resposta"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={submitting}
            rows={3}
          />
          <div>
            <button type="submit" disabled={submitting || !answer.trim()}>
              Enviar
            </button>
          </div>
        </form>
      )}
    </main>
  );
}

export default function PlacementPage() {
  return (
    <Suspense fallback={<main>Carregando…</main>}>
      <PlacementConversation />
    </Suspense>
  );
}
