/**
 * Format number with MetaTrader 5 style (dot as decimal separator)
 * @param value - Number or string to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string (e.g., "0.03", "1.50", "5000.00")
 */
export function formatNumberWithDots(value: number | string, decimals: number = 2): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '';

  // Use standard toFixed with dot as decimal separator (MT5 style)
  return num.toFixed(decimals);
}

/**
 * Parse formatted string back to number
 * Handles standard decimal notation with dot separator
 */
export function parseFormattedNumber(value: string): number {
  if (!value) return 0;
  return parseFloat(value) || 0;
}
