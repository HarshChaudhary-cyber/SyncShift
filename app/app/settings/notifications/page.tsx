'use client';

import LegacyRedirect from '@/components/unified/LegacyRedirect';

export default function LegacyNotificationsSettingsPage() {
  return <LegacyRedirect to="/settings?category=notifications" />;
}
