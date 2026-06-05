export function parseExpiryDateTime(expiryDate, expiryTime) {
  if (!expiryDate || !expiryDate.trim()) return null;
  const cleanedDate = expiryDate.trim();
  let date = null;

  // Try YYYY-MM-DD
  const yyyymmdd = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/.exec(cleanedDate);
  if (yyyymmdd) {
    const year = parseInt(yyyymmdd[1], 10);
    const month = parseInt(yyyymmdd[2], 10) - 1;
    const day = parseInt(yyyymmdd[3], 10);
    date = new Date(year, month, day);
  } else {
    // Try DD-MM-YYYY or DD/MM/YYYY
    const ddmmyyyy = /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/.exec(cleanedDate);
    if (ddmmyyyy) {
      const day = parseInt(ddmmyyyy[1], 10);
      const month = parseInt(ddmmyyyy[2], 10) - 1;
      const year = parseInt(ddmmyyyy[3], 10);
      date = new Date(year, month, day);
    } else {
      // Standard parse fallback
      date = new Date(cleanedDate);
    }
  }

  if (!date || isNaN(date.getTime())) {
    throw new Error('Invalid date format. Please use YYYY-MM-DD or select using the calendar.');
  }

  // Apply time if provided
  if (expiryTime && expiryTime.trim()) {
    const timeParts = /^(\d{1,2}):(\d{2})$/.exec(expiryTime.trim());
    if (timeParts) {
      const hours = parseInt(timeParts[1], 10);
      const minutes = parseInt(timeParts[2], 10);
      date.setHours(hours, minutes, 0, 0);
    } else {
      const timeVal = new Date(`1970-01-01T${expiryTime.trim()}`);
      if (!isNaN(timeVal.getTime())) {
        date.setHours(timeVal.getHours(), timeVal.getMinutes(), 0, 0);
      }
    }
  } else {
    // Time is optional — default to end of that day (23:59:59)
    date.setHours(23, 59, 59, 999);
  }

  // Validate future date
  if (date.getTime() <= Date.now()) {
    throw new Error('Expiration date must be in the future.');
  }

  return date.toISOString();
}
