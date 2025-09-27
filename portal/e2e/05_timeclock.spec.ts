import { test, expect } from '@playwright/test';
import { gotoStaff, hasIds, env, apiPost, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test.describe('timeclock (env driven)', () => {
  test.skip(!env.location, 'E2E_LOCATION_ID required');

  test('@smoke punch in and out', async ({ page, request }) => {
    await apiPost(request, '/timeclock/punch-out', {});

    await gotoStaff(page, '/staff/timeclock');
    await page.fill('input[placeholder="Location UUID"]', env.location);

    const messages: string[] = [];
    page.on('dialog', (dialog) => {
      messages.push(dialog.message());
      dialog.accept();
    });

    await page.click('button:has-text("Punch in")');
    await page.waitForTimeout(500);
    await page.click('button:has-text("Punch out")');
    await page.waitForTimeout(500);

    expect(messages.some((msg) => msg.includes('Punched in'))).toBeTruthy();
    expect(messages.some((msg) => msg.includes('Punched out'))).toBeTruthy();
  });
});
