'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { GamificationProfileResponse, ProgressionProfileResponse } from '@/services/types';

const SKILL_LABELS: Record<string, string> = {
  reading: 'Leitura',
  writing: 'Escrita',
  speaking: 'Fala',
  listening: 'Escuta',
};

export default function ProgressPage() {
  const [gamification, setGamification] = useState<GamificationProfileResponse | null>(null);
  const [progression, setProgression] = useState<ProgressionProfileResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/gamification/profile').then((res) => {
        if (!res.ok) throw new Error('Could not load your gamification profile');
        return res.json();
      }),
      fetch('/api/progression/profile').then((res) => {
        if (!res.ok) throw new Error('Could not load your progression profile');
        return res.json();
      }),
    ])
      .then(([gamificationData, progressionData]) => {
        setGamification(gamificationData);
        setProgression(progressionData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      <h1>Seu progresso</h1>
      <nav>
        <Link href="/learn">Exercícios</Link> · <Link href="/learn/conversation">Conversa</Link>
      </nav>

      {loading && <p>Carregando…</p>}
      {error && <p role="alert">{error}</p>}

      {gamification && (
        <section>
          <h2>Gamificação</h2>
          <p>XP total: {gamification.xp_total}</p>
          <p>Sequência atual: {gamification.streak_current} dia(s)</p>
          {gamification.badges.length > 0 ? (
            <ul>
              {gamification.badges.map((badge) => (
                <li key={badge.code}>
                  🏅 <strong>{badge.name}</strong> — {badge.description}
                </li>
              ))}
            </ul>
          ) : (
            <p>Nenhum emblema conquistado ainda.</p>
          )}
        </section>
      )}

      {progression && (
        <section>
          <h2>Níveis por habilidade</h2>
          <ul>
            {progression.skills.map((skill) => (
              <li key={skill.skill}>
                <strong>{SKILL_LABELS[skill.skill] ?? skill.skill}:</strong> {skill.cefr_level} (
                {skill.mastery_score}% do nível atual)
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
