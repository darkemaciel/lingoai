import type { GamificationDelta } from '@/services/types';

const BADGE_NAMES: Record<string, string> = {
  first_conversation_completed: 'Primeira Conversa',
  streak_7_days: 'Sequência de 7 Dias',
  first_level_advanced: 'Subiu de Nível!',
};

export default function GamificationFeedback({ delta }: { delta: GamificationDelta }) {
  return (
    <aside aria-live="polite">
      <p>
        +{delta.xp_awarded} XP <span>(total: {delta.xp_total})</span>
      </p>
      <p>Sequência atual: {delta.streak_current} dia(s)</p>
      {delta.badges_unlocked.length > 0 && (
        <ul>
          {delta.badges_unlocked.map((code) => (
            <li key={code}>🏅 {BADGE_NAMES[code] ?? code}</li>
          ))}
        </ul>
      )}
    </aside>
  );
}
