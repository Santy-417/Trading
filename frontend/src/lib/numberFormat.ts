/**
 * Format number with thousand separators using DOTS (European format)
 * @param value - Number or string to format
 * @param decimals - Number of decimal places (default: 0 for integers)
 * @returns Formatted string (e.g., "5.000" or "2.575,50")
 */
export function formatNumberWithDots(value: number | string, decimals: number = 0): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '';

  const parts = num.toFixed(decimals).split('.');
  // Add thousand separators (dots)
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  // Join with comma for decimal separator (if decimals > 0)
  return decimals > 0 ? parts.join(',') : parts[0];
}

/**
 * Parse formatted string back to number
 * Handles: "5.000" (thousand sep) and "2.575,50" (with decimals)
 */
export function parseFormattedNumber(value: string): number {
  if (!value) return 0;
  // Remove thousand separators (dots), replace comma with dot for decimal
  const cleaned = value.replace(/\./g, '').replace(',', '.');
  return parseFloat(cleaned) || 0;
}
