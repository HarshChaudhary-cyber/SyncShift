'use client';

import React from 'react';

export interface OAuthButtonsProps {
  onSuccessRedirect?: string;
  className?: string;
  captchaToken?: string;
  onError?: (msg: string) => void;
}

export function OAuthButtons(_props: OAuthButtonsProps) {
  // Third-party Google and Microsoft sign-in buttons are removed in favor of
  // institutional university authentication.
  return null;
}

export function OAuthDivider(_props: { text?: string }) {
  return null;
}

export default OAuthButtons;
