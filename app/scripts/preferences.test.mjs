import { test } from 'node:test';
import assert from 'node:assert/strict';

function getUserPrefKey(userId, key) {
  if (userId) return `syncshift_user_${userId}_${key}`;
  return `syncshift_guest_${key}`;
}

function formatTimeDisplay(timeStr, formatMode = '12h') {
  if (!timeStr) return '';
  const [hStr, mStr] = timeStr.split(':');
  const hour = parseInt(hStr, 10);
  const minute = parseInt(mStr || '0', 10);
  if (isNaN(hour)) return timeStr;

  if (formatMode === '24h') {
    return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  }

  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  const minuteFormatted = minute === 0 ? '' : `:${String(minute).padStart(2, '0')}`;
  return `${displayHour}${minuteFormatted} ${period}`;
}

function formatTimeRangeDisplay(startTime, endTime, formatMode = '12h') {
  if (!startTime || !endTime) return '';
  if (formatMode === '24h') {
    return `${startTime.slice(0, 5)}–${endTime.slice(0, 5)}`;
  }
  return `${formatTimeDisplay(startTime, '12h')} – ${formatTimeDisplay(endTime, '12h')}`;
}

test('user-scoped localStorage keys isolate accounts', () => {
  assert.equal(getUserPrefKey(101, 'theme'), 'syncshift_user_101_theme');
  assert.equal(getUserPrefKey(202, 'time_format'), 'syncshift_user_202_time_format');
  assert.equal(getUserPrefKey(null, 'calendar_view'), 'syncshift_guest_calendar_view');
});

test('formatTimeDisplay formats 12h and 24h times correctly', () => {
  assert.equal(formatTimeDisplay('09:00', '12h'), '9 AM');
  assert.equal(formatTimeDisplay('09:30', '12h'), '9:30 AM');
  assert.equal(formatTimeDisplay('14:45', '12h'), '2:45 PM');
  assert.equal(formatTimeDisplay('00:00', '12h'), '12 AM');
  assert.equal(formatTimeDisplay('12:00', '12h'), '12 PM');

  assert.equal(formatTimeDisplay('09:00', '24h'), '09:00');
  assert.equal(formatTimeDisplay('14:45', '24h'), '14:45');
  assert.equal(formatTimeDisplay('00:00', '24h'), '00:00');
});

test('formatTimeRangeDisplay handles 12h vs 24h intervals', () => {
  assert.equal(formatTimeRangeDisplay('09:00', '10:30', '24h'), '09:00–10:30');
  assert.equal(formatTimeRangeDisplay('09:00', '10:30', '12h'), '9 AM – 10:30 AM');
  assert.equal(formatTimeRangeDisplay('13:00', '14:30', '12h'), '1 PM – 2:30 PM');
});

test('role-specific suggestions map to authoritative roles', () => {
  const getSuggestions = (role) => {
    if (role === 'super_admin' || role === 'admin') return ['rooms', 'versions', 'draft'];
    if (role === 'faculty' || role === 'professor') return ['teaching', 'office hours', 'meetings'];
    return ['classes', 'shifts', 'conflicts'];
  };

  assert.deepEqual(getSuggestions('student'), ['classes', 'shifts', 'conflicts']);
  assert.deepEqual(getSuggestions('professor'), ['teaching', 'office hours', 'meetings']);
  assert.deepEqual(getSuggestions('faculty'), ['teaching', 'office hours', 'meetings']);
  assert.deepEqual(getSuggestions('admin'), ['rooms', 'versions', 'draft']);
  assert.deepEqual(getSuggestions('super_admin'), ['rooms', 'versions', 'draft']);
});
