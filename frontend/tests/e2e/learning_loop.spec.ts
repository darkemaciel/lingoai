import { test, expect } from '@playwright/test';

// Independent Test (spec.md US2): with a pre-existing placed student,
// complete one activity and verify inline XP/streak feedback appears and
// matches the persistent progress panel (FR-19, SC-007). Runs against the
// full docker-compose stack with AI_PROVIDER=local (deterministic).

async function completePlacement(page: import('@playwright/test').Page) {
  const email = `learner-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByLabel('E-mail').fill(email);
  await page.getByLabel('Senha').fill('correct-horse-battery-staple');
  await page.getByRole('button', { name: /criar conta/i }).click();

  await page.waitForURL(/\/placement\?sessionId=/);
  for (let turn = 0; turn < 3; turn += 1) {
    await page.getByLabel('Sua resposta').fill(`Placement answer ${turn + 1}.`);
    await page.getByRole('button', { name: 'Enviar' }).click();
  }
  await page.waitForURL(/\/placement\/result\?sessionId=/);
}

test('learning loop shows inline gamification feedback matching the progress panel', async ({
  page,
}) => {
  await completePlacement(page);

  await page.getByRole('link', { name: /começar a praticar/i }).click();
  await page.waitForURL('/learn');

  await page.getByLabel('Sua resposta').fill('I practice English every single day with friends.');
  await page.getByRole('button', { name: 'Enviar resposta' }).click();

  const inlineXp = page.getByText(/^\+\d+ XP/);
  await expect(inlineXp).toBeVisible();
  const inlineText = await inlineXp.textContent();
  const totalMatch = inlineText?.match(/total:\s*(\d+)/);
  expect(totalMatch).not.toBeNull();
  const inlineXpTotal = totalMatch?.[1];

  await page.goto('/progress');
  await expect(page.getByText(`XP total: ${inlineXpTotal}`)).toBeVisible();
});
