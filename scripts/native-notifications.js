import { LocalNotifications } from '@capacitor/local-notifications';
import { registerPlugin } from '@capacitor/core';
import { Share } from '@capacitor/share';

// Bundle Capacitor's notification bridge into the app. Do not depend on a
// remote CDN at runtime: the permission button must work offline as well.
if (window.Capacitor?.isNativePlatform?.()) {
  window.ZadLocalNotifications = LocalNotifications;
  window.ZadPrayerAlarm = registerPlugin('PrayerAlarm');
  window.ZadCompass = registerPlugin('Compass');
  window.ZadNativeShare = Share;
}
