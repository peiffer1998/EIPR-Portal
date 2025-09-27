import { test, expect } from '@playwright/test';
import { gotoStaff, assertHeader, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test('@smoke reservations page renders table', async ({ page }) => {
  await gotoStaff(page, '/staff/reservations');
  await assertHeader(page, 'Reservations');
  await expect(page.locator('table')).toBeVisible();
});
