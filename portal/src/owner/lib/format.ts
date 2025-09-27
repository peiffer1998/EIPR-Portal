const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

export const formatCurrency = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) return currencyFormatter.format(0);
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(numeric)) return currencyFormatter.format(0);
  return currencyFormatter.format(Number(numeric));
};
