import { test, expect } from '@playwright/test';
import { gotoStaff, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test('@smoke waitlist page shows placeholder', async ({ page }) => {
  await gotoStaff(page, '/staff/waitlist');
  await expect(page.getByText('Waitlist tooling coming soon.')).toBeVisible();
});

test('@smoke waitlist create entry (pending implementation)', async () => {
  test.skip(true, 'Waitlist UI does not yet support automated flow');
});
