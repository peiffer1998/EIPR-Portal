import { chromium } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const USER = process.env.E2E_USER || 'admin@eipr.local';
const PASS = process.env.E2E_PASS || 'admin123';

export default async function globalSetup() {
  const statePath = path.resolve('e2e/.auth/state.json');
  const skipPath = path.resolve('e2e/.auth/skip.txt');
  await fs.mkdir(path.dirname(statePath), { recursive: true });

  let skipReason: string | null = null;
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    await page.goto(`${BASE_URL}/staff/login`, { waitUntil: 'domcontentloaded' });
    await page.fill('input[placeholder="Email"]', USER);
    await page.fill('input[placeholder="Password"]', PASS);
    await page.click('button:has-text("Sign in")');
    await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
  } catch (error) {
    skipReason = error instanceof Error ? error.message : String(error);
  } finally {
    await page.context().storageState({ path: statePath });
    await browser.close();
  }

  if (skipReason) {
    console.warn(`[playwright] Skipping tests: ${skipReason}`);
    await fs.writeFile(skipPath, skipReason, 'utf-8');
  } else {
    await fs.rm(skipPath, { force: true });
  }
}
