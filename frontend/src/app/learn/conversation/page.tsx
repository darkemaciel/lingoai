'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import GamificationFeedback from '@/components/GamificationFeedback';
import type { GamificationDelta } from '@/services/types';

interface Turn {
  speaker: 'agent' | 'student';
  text: string;
}

export default function LearnConversationPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastDelta, setLastDelta] = useState<GamificationDelta | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/conversations', { method: 'POST' })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error?.message ?? 'Could not start the conversation');
        }
        return res.json();
      })
      .then((data) => setConversationId(data.conversation_session_id))
      .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!conversationId || !message.trim()) return;
    setError(null);
    setSubmitting(true);
    const studentText = message;
    setTurns((prev) => [...prev, { speaker: 'student', text: studentText }]);
    setMessage('');
    setLastDelta(null);

    try {
      const res = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_submission_id: crypto.randomUUID(),
          content_text: studentText,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error?.message ?? 'Could not send your message');
      }
      const data = await res.json();
      setTurns((prev) => [...prev, { speaker: 'agent', text: data.agent_message.content_text }]);
      if (data.gamification_delta) {
        setLastDelta(data.gamification_delta);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Conversa</h1>
      <nav>
        <Link href="/learn">Ir para exercícios</Link> · <Link href="/progress">Ver progresso</Link>
      </nav>

      <div aria-live="polite">
        {turns.map((turn, index) => (
          <p key={index}>
            <strong>{turn.speaker === 'agent' ? 'IA' : 'Você'}:</strong> {turn.text}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>

      {lastDelta && <GamificationFeedback delta={lastDelta} />}
      {error && <p role="alert">{error}</p>}

      <form onSubmit={handleSubmit}>
        <textarea
          aria-label="Sua mensagem"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={submitting || !conversationId}
          rows={3}
        />
        <div>
          <button type="submit" disabled={submitting || !message.trim() || !conversationId}>
            Enviar
          </button>
        </div>
      </form>
    </main>
  );
}
