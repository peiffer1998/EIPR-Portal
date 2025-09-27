export function fmtDateTime(input: string | number | Date): string {
  const value =
    typeof input === 'string' || typeof input === 'number' ? new Date(input) : input;
  return value.toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function fmtDate(input: string | number | Date): string {
  const value =
    typeof input === 'string' || typeof input === 'number' ? new Date(input) : input;
  return value.toLocaleDateString('en-US', {
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });
}
