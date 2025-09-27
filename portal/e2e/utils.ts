import { expect, Page, type APIRequestContext } from '@playwright/test';
import fs from 'fs';
import path from 'path';

export const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';
export const API_URL = process.env.E2E_API_URL || 'http://localhost:8000/api/v1';

export const env = {
  location: process.env.E2E_LOCATION_ID || '',
  owner: process.env.E2E_OWNER_ID || '',
  pet: process.env.E2E_PET_ID || '',
  specialist: process.env.E2E_SPECIALIST_ID || '',
  service: process.env.E2E_SERVICE_ID || '',
};

export function hasIds(...keys: (keyof typeof env)[]) {
  return keys.every((key) => env[key] && String(env[key]).length > 0);
}

export async function gotoStaff(page: Page, path: string) {
  await page.goto(`${BASE_URL}${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
}

export async function assertHeader(page: Page, title: string) {
  await expect(page.locator('.page-title', { hasText: title })).toBeVisible();
}

async function fetchToken(request: APIRequestContext) {
  const user = process.env.E2E_USER || 'admin@eipr.local';
  const pass = process.env.E2E_PASS || 'admin123';
  const body = new URLSearchParams();
  body.set('username', user);
  body.set('password', pass);
  const res = await request.post(`${API_URL}/auth/token`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  if (!res.ok()) throw new Error('Failed to fetch token');
  const data: any = await res.json();
  return String(data.access_token || '');
}

export async function apiGet<T>(request: APIRequestContext, path: string, token?: string): Promise<T | null> {
  const auth = token || (await fetchToken(request));
  if (!auth) return null;
  const res = await request.get(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${auth}` } });
  if (!res.ok()) return null;
  return (await res.json()) as T;
}

export async function apiPost<T>(request: APIRequestContext, path: string, body: any, token?: string) {
  const auth = token || (await fetchToken(request));
  const res = await request.post(`${API_URL}${path}`, {
    data: body,
    headers: { Authorization: `Bearer ${auth}` },
  });
  return res;
}

export function getSkipReason(): string | null {
  try {
    const filePath = path.join(process.cwd(), 'e2e', '.auth', 'skip.txt');
    const contents = fs.readFileSync(filePath, 'utf-8').trim();
    if (!contents) return null;
    return contents.includes('\n') ? contents.split('\n')[0] : contents;
  } catch {
    return null;
  }
}
