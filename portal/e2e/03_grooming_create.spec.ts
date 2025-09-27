import { test, expect } from '@playwright/test';
import { gotoStaff, hasIds, env, apiGet, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test.describe('grooming create (env driven)', () => {
  test.skip(!hasIds('owner', 'pet', 'specialist', 'service'), 'E2E_OWNER_ID/E2E_PET_ID/E2E_SPECIALIST_ID/E2E_SERVICE_ID required');

  test('@smoke create grooming appointment', async ({ page, request }) => {
    const owner = await apiGet<any>(request, `/owners/${env.owner}`);
    const pet = await apiGet<any>(request, `/pets/${env.pet}`);
    test.skip(!owner, `Owner ${env.owner} not found`);
    test.skip(!pet, `Pet ${env.pet} not found`);

    await gotoStaff(page, '/staff/grooming/new');
    await expect(page.getByText('Book grooming appointment')).toBeVisible();

    const ownerSearch = page.locator('input[placeholder="Search"]').first();
    await ownerSearch.fill(owner.email || owner.last_name || owner.id);
    await page.waitForTimeout(600);
    const ownerButton = page.locator('button', { hasText: owner.email || owner.last_name || owner.id }).first();
    await ownerButton.waitFor({ state: 'visible' });
    await ownerButton.click();

    const petSearch = page.locator('input[placeholder="Search"]').nth(1);
    await petSearch.fill(pet.name || pet.id);
    await page.waitForTimeout(600);
    const petButton = page.locator('button', { hasText: pet.name || pet.id }).first();
    await petButton.waitFor({ state: 'visible' });
    await petButton.click();

    if (env.location) {
      await page.fill('input[name="location_id"]', env.location);
    }
    await page.fill('input[name="specialist_id"]', env.specialist);
    await page.fill('input[name="service_id"]', env.service);

    const startAt = new Date(Date.now() + 20 * 60 * 1000).toISOString().slice(0, 16);
    await page.fill('input[type="datetime-local"]', startAt);

    let alertMessage = '';
    page.once('dialog', (dialog) => {
      alertMessage = dialog.message();
      dialog.accept();
    });

    await page.click('button:has-text("Book")');
    await page.waitForTimeout(500);
    expect(alertMessage).toContain('Appointment created');
  });
});
