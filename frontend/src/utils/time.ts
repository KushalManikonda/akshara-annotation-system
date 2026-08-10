/**
 * Format total seconds into natural duration format:
 * "X hrs, Y mins" or "1 hr, 25 mins"
 */
export function formatDurationHoursMins(seconds: number | undefined | null): string {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds <= 0) {
    return '0 hrs, 0 mins';
  }
  const totalMins = Math.floor(seconds / 60);
  const hrs = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  const hrsStr = hrs === 1 ? '1 hr' : `${hrs} hrs`;
  return `${hrsStr}, ${mins} mins`;
}

/**
 * Format ISO date string or Date object into Indian format: DD/MM/YYYY
 * e.g. "09/08/2026"
 */
export function formatDateIndian(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return '-';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return '-';
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}
