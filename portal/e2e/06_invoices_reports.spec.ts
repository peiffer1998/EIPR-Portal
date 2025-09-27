import { test, expect } from '@playwright/test';
import { gotoStaff, assertHeader, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test('@smoke invoices and reports pages render', async ({ page }) => {
  await gotoStaff(page, '/staff/invoices');
  await assertHeader(page, 'Invoices');
  await expect(page.locator('table')).toBeVisible();

  await gotoStaff(page, '/staff/reports');
  await assertHeader(page, 'Reports');
  await expect(page.getByRole('button', { name: 'Revenue' })).toBeVisible();
});
