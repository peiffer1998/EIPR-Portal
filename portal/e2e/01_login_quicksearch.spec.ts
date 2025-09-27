import { test, expect } from '@playwright/test';
import { gotoStaff, assertHeader, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

const metaKey = process.platform === 'darwin' ? 'Meta' : 'Control';

test('@smoke dashboard renders and quick search opens', async ({ page }) => {
  await gotoStaff(page, '/staff');
  await assertHeader(page, 'Dashboard');

  await page.keyboard.down(metaKey);
  await page.keyboard.press('KeyK');
  await page.keyboard.up(metaKey);

  await expect(page.getByPlaceholder('Search owners or pets')).toBeVisible();
});
