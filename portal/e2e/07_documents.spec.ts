import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { gotoStaff, env, apiGet, getSkipReason } from './utils';

const skipReason = getSkipReason();
if (skipReason) {
  test.skip(true, skipReason);
}

test.describe('documents (env driven)', () => {
  test.skip(!env.owner, 'E2E_OWNER_ID required for document workflow');

  test('@smoke upload document and see in table', async ({ page, request }) => {
    const owner = await apiGet<any>(request, `/owners/${env.owner}`);
    test.skip(!owner, `Owner ${env.owner} not found`);

    await gotoStaff(page, '/staff/ops/files');

    const ownerSearch = page.locator('input[placeholder="Search"]').first();
    await ownerSearch.fill(owner.email || owner.last_name || owner.id);
    await page.waitForTimeout(600);
    const ownerButton = page.locator('button', { hasText: owner.email || owner.last_name || owner.id }).first();
    await ownerButton.waitFor({ state: 'visible' });
    await ownerButton.click();

    const tmpDir = path.join(process.cwd(), 'e2e', 'tmp');
    fs.mkdirSync(tmpDir, { recursive: true });
    const filename = `pw-doc-${Date.now()}.txt`;
    const filePath = path.join(tmpDir, filename);
    fs.writeFileSync(filePath, 'document from playwright');

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(filePath);

    await expect(page.locator('tbody tr', { hasText: filename })).toBeVisible({ timeout: 15_000 });

    fs.unlinkSync(filePath);
  });
});
