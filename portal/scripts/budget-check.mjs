import { readdirSync, statSync } from 'fs';
import { join } from 'path';

const distDir = 'dist/assets';
let totalJs = 0;
let totalCss = 0;

for (const file of readdirSync(distDir)) {
  const size = statSync(join(distDir, file)).size;
  if (file.endsWith('.js')) totalJs += size;
  if (file.endsWith('.css')) totalCss += size;
}

const mb = (bytes) => bytes / 1024 / 1024;
const jsBudget = Number(process.env.BUDGET_JS_MB ?? '3');
const cssBudget = Number(process.env.BUDGET_CSS_MB ?? '1');

const jsSizeMb = mb(totalJs);
const cssSizeMb = mb(totalCss);

console.log(`[bundle] JS ${jsSizeMb.toFixed(2)} MB (budget ${jsBudget} MB)`);
console.log(`[bundle] CSS ${cssSizeMb.toFixed(2)} MB (budget ${cssBudget} MB)`);

if (jsSizeMb > jsBudget) {
  console.error('ERROR: JS bundle exceeds budget');
  process.exit(1);
}
if (cssSizeMb > cssBudget) {
  console.error('ERROR: CSS bundle exceeds budget');
  process.exit(1);
}
