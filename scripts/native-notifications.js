import { LocalNotifications } from '@capacitor/local-notifications';
import { registerPlugin } from '@capacitor/core';

// Bundle Capacitor's notification bridge into the app. Do not depend on a
// remote CDN at runtime: the permission button must work offline as well.
if (window.Capacitor?.isNativePlatform?.()) {
  window.ZadLocalNotifications = LocalNotifications;
  window.ZadPrayerAlarm = registerPlugin('PrayerAlarm');
}
