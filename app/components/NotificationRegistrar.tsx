'use client';

import { useEffect, useRef } from 'react';
import { useAuthContext } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { urlBase64ToUint8Array } from '@/lib/notificationHelpers';

export default function NotificationRegistrar() {
  const { user } = useAuthContext();
  const registeredRef = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      return;
    }

    if (!user) {
      return;
    }

    if (registeredRef.current) {
      return;
    }
    registeredRef.current = true;

    async function initPush() {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        await navigator.serviceWorker.ready;

        const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
        if (!vapidPublicKey) {
          console.warn('SyncShift: NEXT_PUBLIC_VAPID_PUBLIC_KEY is not defined.');
          return;
        }

        // Check or request permission
        let permission = Notification.permission;
        if (permission === 'default') {
          permission = await Notification.requestPermission();
        }

        if (permission !== 'granted') {
          return;
        }

        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
          });
        }

        if (subscription) {
          const subJson = subscription.toJSON();
          if (subJson.endpoint && subJson.keys?.p256dh && subJson.keys?.auth) {
            await api.subscribePush({
              endpoint: subJson.endpoint,
              expirationTime: subJson.expirationTime,
              keys: {
                p256dh: subJson.keys.p256dh,
                auth: subJson.keys.auth,
              },
            });
          }
        }
      } catch (err) {
        console.warn('SyncShift notification registration:', err);
      }
    }

    initPush();
  }, [user]);

  return null;
}
