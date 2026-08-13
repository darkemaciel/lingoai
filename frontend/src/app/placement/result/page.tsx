'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import type { PlacementResult } from '@/services/types';

const SKILL_LABELS: Record<string, string> = {
  reading_level: 'Leitura',
  writing_level: 'Escrita',
  speaking_level: 'Fala',
  listening_level: 'Escuta',
};

function PlacementResultSummary() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('sessionId');

  const [result, setResult] = useState<PlacementResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) {
      setError('Sessão de nivelamento não encontrada.');
      setLoading(false);
      return;
    }
    fetch(`/api/placement/sessions/${sessionId}/result`)
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error?.message ?? 'Could not load result');
        }
        return res.json();
      })
      .then((data: PlacementResult) => setResult(data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <main>Calculando seu nível…</main>;
  if (error) return <main role="alert">{error}</main>;
  if (!result) return null;

  return (
    <main>
      <h1>Seu resultado de nivelamento</h1>
      <ul>
        {(Object.keys(SKILL_LABELS) as (keyof PlacementResult)[]).map((key) => {
          const level = result[key];
          if (!level) return null;
          return (
            <li key={key}>
              <strong>{SKILL_LABELS[key]}:</strong> {String(level)}
            </li>
          );
        })}
      </ul>
      <section>
        <h2>Pontos fortes</h2>
        <p>{result.strengths_summary}</p>
      </section>
      <section>
        <h2>Pontos a desenvolver</h2>
        <p>{result.weaknesses_summary}</p>
      </section>
      <Link href="/learn">Começar a praticar</Link>
    </main>
  );
}

export default function PlacementResultPage() {
  return (
    <Suspense fallback={<main>Carregando…</main>}>
      <PlacementResultSummary />
    </Suspense>
  );
}
