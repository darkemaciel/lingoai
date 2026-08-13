import { test, expect } from '@playwright/test';

// Independent Test (spec.md US1): register a new account, complete the
// placement conversation in text, verify a per-skill level result is
// generated and displayed. Runs against the full docker-compose stack
// (frontend on :3000, backend on :8000, AI_PROVIDER=local so the
// LocalModelAdapter's canned 3-turn placement flow is deterministic).

test('register, complete placement conversation, see result', async ({ page }) => {
  const email = `learner-${Date.now()}@example.com`;

  await page.goto('/register');
  await page.getByLabel('E-mail').fill(email);
  await page.getByLabel('Senha').fill('correct-horse-battery-staple');
  await page.getByRole('button', { name: /criar conta/i }).click();

  await page.waitForURL(/\/placement\?sessionId=/);

  // LocalModelAdapter completes a placement session after
  // ASSESSMENT_TURNS_BEFORE_COMPLETE (3) student answers.
  for (let turn = 0; turn < 3; turn += 1) {
    const textarea = page.getByLabel('Sua resposta');
    await textarea.fill(`This is my placement answer number ${turn + 1}.`);
    await page.getByRole('button', { name: 'Enviar' }).click();
  }

  await page.waitForURL(/\/placement\/result\?sessionId=/);
  await expect(page.getByRole('heading', { name: /resultado de nivelamento/i })).toBeVisible();
  await expect(page.getByText(/Leitura:/)).toBeVisible();
  await expect(page.getByText(/Escrita:/)).toBeVisible();
});
