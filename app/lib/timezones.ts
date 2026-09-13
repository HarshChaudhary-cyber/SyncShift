/**
 * Comprehensive IANA Timezones grouped by geographic region with calculated UTC offsets
 */

export interface TimezoneOption {
  value: string;
  label: string;
  offset: string;
  group: string;
}

const RAW_TIMEZONES = [
  // Europe
  'Europe/London',
  'Europe/Dublin',
  'Europe/Berlin',
  'Europe/Paris',
  'Europe/Amsterdam',
  'Europe/Brussels',
  'Europe/Madrid',
  'Europe/Rome',
  'Europe/Vienna',
  'Europe/Zurich',
  'Europe/Warsaw',
  'Europe/Prague',
  'Europe/Budapest',
  'Europe/Stockholm',
  'Europe/Oslo',
  'Europe/Copenhagen',
  'Europe/Helsinki',
  'Europe/Athens',
  'Europe/Bucharest',
  'Europe/Kiev',
  'Europe/Moscow',
  'Europe/Istanbul',
  'Europe/Lisbon',

  // Asia
  'Asia/Kolkata',
  'Asia/Dubai',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Asia/Hong_Kong',
  'Asia/Seoul',
  'Asia/Shanghai',
  'Asia/Taipei',
  'Asia/Bangkok',
  'Asia/Jakarta',
  'Asia/Kuala_Lumpur',
  'Asia/Manila',
  'Asia/Ho_Chi_Minh',
  'Asia/Karachi',
  'Asia/Dhaka',
  'Asia/Colombo',
  'Asia/Kathmandu',
  'Asia/Riyadh',
  'Asia/Qatar',
  'Asia/Jerusalem',
  'Asia/Beirut',
  'Asia/Almaty',
  'Asia/Tashkent',

  // Americas - North & South
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'America/Honolulu',
  'America/Phoenix',
  'America/Toronto',
  'America/Vancouver',
  'America/Montreal',
  'America/Calgary',
  'America/Mexico_City',
  'America/Bogota',
  'America/Lima',
  'America/Santiago',
  'America/Buenos_Aires',
  'America/Sao_Paulo',
  'America/Caracas',

  // Australia & Pacific
  'Australia/Sydney',
  'Australia/Melbourne',
  'Australia/Brisbane',
  'Australia/Adelaide',
  'Australia/Perth',
  'Australia/Hobart',
  'Pacific/Auckland',
  'Pacific/Fiji',
  'Pacific/Guam',

  // Africa
  'Africa/Cairo',
  'Africa/Johannesburg',
  'Africa/Lagos',
  'Africa/Nairobi',
  'Africa/Casablanca',
  'Africa/Accra',
  'Africa/Addis_Ababa',

  // UTC
  'UTC',
];

/**
 * Calculates current UTC offset string, e.g. "UTC+05:30" or "UTC-04:00"
 */
export function getTimezoneOffset(tz: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      timeZoneName: 'shortOffset',
    });
    const parts = formatter.formatToParts(new Date());
    const part = parts.find((p) => p.type === 'timeZoneName');
    if (part?.value) {
      return part.value.replace('GMT', 'UTC');
    }
    return 'UTC';
  } catch {
    return 'UTC';
  }
}

/**
 * Pre-formatted list of timezone options for CustomSelect
 */
export const TIMEZONE_OPTIONS: TimezoneOption[] = RAW_TIMEZONES.map((tz) => {
  const parts = tz.split('/');
  const group = parts.length > 1 ? parts[0] : 'Universal';
  const city = parts.length > 1 ? parts.slice(1).join('/').replace(/_/g, ' ') : tz;
  const offset = getTimezoneOffset(tz);
  return {
    value: tz,
    label: `${tz} (${offset})`,
    offset,
    group,
  };
});
