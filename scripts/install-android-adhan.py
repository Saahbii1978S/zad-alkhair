from pathlib import Path
import re, subprocess
root=Path("android/app/src/main")
java=root/"java/org/zadalkhair/app"
java.mkdir(parents=True,exist_ok=True)
(java/"PrayerAlarmPlugin.java").write_text(r'''package org.zadalkhair.app;
import android.app.AlarmManager;
import android.content.Context;
import android.os.Build;
import com.getcapacitor.*;
import com.getcapacitor.annotation.*;
import org.json.JSONArray;
@CapacitorPlugin(name="PrayerAlarm")
public class PrayerAlarmPlugin extends Plugin {
 @PluginMethod public void schedule(PluginCall call) {
  String times=call.getString("times");
  if(times==null)times="[]";
  try {
   JSONArray arr=new JSONArray(times);
   getContext().getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).edit().putString("times",arr.toString()).apply();
   String sound=call.getString("sound","default");
   if(!"default".equals(sound)&&!"mecca".equals(sound)&&!"madinah".equals(sound)&&!"general2".equals(sound))sound="default";
   getContext().getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).edit().putString("sound",sound).apply();
   PrayerAlarmReceiver.scheduleAll(getContext(),arr);
   call.resolve();
  } catch(Exception e) { call.reject("تعذّر ضبط أوقات الأذان: "+e.getMessage()); }
 }
 @PluginMethod public void cancel(PluginCall call) {
  getContext().getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).edit().remove("times").apply();
  PrayerAlarmReceiver.cancelAll(getContext());
  call.resolve();
 }
}
''',encoding="utf-8")
(java/"PrayerAlarmReceiver.java").write_text(r'''package org.zadalkhair.app;
import android.app.*;
import android.content.*;
import android.os.Build;
import org.json.*;
import java.util.Calendar;
public class PrayerAlarmReceiver extends BroadcastReceiver {
 static final int BASE=82000;
 static PendingIntent pending(Context c,int id,int h,int m) {
  Intent i=new Intent(c,PrayerAlarmReceiver.class).putExtra("hour",h).putExtra("minute",m).putExtra("alarmId",id);
  return PendingIntent.getBroadcast(c,BASE+id,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
 }
 static void set(Context c,int id,int h,int m) {
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  if(am==null)return;
  Calendar at=Calendar.getInstance(); at.set(Calendar.HOUR_OF_DAY,h); at.set(Calendar.MINUTE,m); at.set(Calendar.SECOND,0); at.set(Calendar.MILLISECOND,0);
  if(at.getTimeInMillis()<=System.currentTimeMillis())at.add(Calendar.DAY_OF_YEAR,1);
  long when=at.getTimeInMillis();
  PendingIntent pi=pending(c,id,h,m);
  if(Build.VERSION.SDK_INT>=23)am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,when,pi);
  else am.setExact(AlarmManager.RTC_WAKEUP,when,pi);
 }
 static void scheduleAll(Context c,JSONArray a) throws Exception {
  cancelAll(c);
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  if(Build.VERSION.SDK_INT>=31 && am!=null && !am.canScheduleExactAlarms())throw new IllegalStateException("فعّل إذن المنبّهات الدقيقة من إعدادات الهاتف");
  for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);set(c,i,o.getInt("hour"),o.getInt("minute"));}
 }
 static void cancelAll(Context c) {
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  for(int i=0;i<5;i++){PendingIntent pi=pending(c,i,0,0);if(am!=null)am.cancel(pi);pi.cancel();}
 }
 @Override public void onReceive(Context c,Intent i) {
  int h=i.getIntExtra("hour",-1),m=i.getIntExtra("minute",-1),id=i.getIntExtra("alarmId",-1);
  if(h<0||m<0)return;
  set(c,id,h,m);
  Intent service=new Intent(c,AdhanPlaybackService.class);
  if(Build.VERSION.SDK_INT>=26)c.startForegroundService(service);else c.startService(service);
 }
 static void restore(Context c) {
  try {
   String s=c.getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).getString("times","[]");
   scheduleAll(c,new JSONArray(s));
  } catch(Exception ignored) {}
 }
}
''',encoding="utf-8")
(java/"PrayerBootReceiver.java").write_text(r'''package org.zadalkhair.app;
import android.content.*;
public class PrayerBootReceiver extends BroadcastReceiver {
 @Override public void onReceive(Context c,Intent i){PrayerAlarmReceiver.restore(c);}
}
''',encoding="utf-8")
(java/"AdhanPlaybackService.java").write_text(r'''package org.zadalkhair.app;
import android.app.*;
import android.content.*;
import android.media.*;
import android.os.*;
public class AdhanPlaybackService extends Service {
 private MediaPlayer player;
 private static final String CHANNEL="zad-full-adhan";
 @Override public void onCreate(){super.onCreate();if(Build.VERSION.SDK_INT>=26){NotificationChannel ch=new NotificationChannel(CHANNEL,"أذان زاد الخير",NotificationManager.IMPORTANCE_HIGH);ch.setDescription("تشغيل الأذان الكامل عند دخول وقت الصلاة");((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).createNotificationChannel(ch);}}
 @Override public int onStartCommand(Intent intent,int flags,int startId){
  Intent open=getPackageManager().getLaunchIntentForPackage(getPackageName());
  PendingIntent pi=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CHANNEL):new Notification.Builder(this);
  startForeground(82090,b.setSmallIcon(getApplicationInfo().icon).setContentTitle("زاد الخير").setContentText("حان وقت الصلاة — الأذان يعمل").setContentIntent(pi).setOngoing(true).build());
  try {
   if(player!=null){player.release();player=null;}
   String selected=getSharedPreferences("zad_prayer_alarms",MODE_PRIVATE).getString("sound","default");
   int audio=R.raw.adhan_default;
   if("mecca".equals(selected))audio=R.raw.adhan_mecca;
   else if("madinah".equals(selected))audio=R.raw.adhan_madinah;
   else if("general2".equals(selected))audio=R.raw.adhan_general2;
   player=MediaPlayer.create(this,audio);
   if(player==null){stopSelf(startId);return START_NOT_STICKY;}
   player.setOnCompletionListener(mp->{mp.release();player=null;stopForeground(true);stopSelf();});
   player.setOnErrorListener((mp,what,extra)->{stopForeground(true);stopSelf();return true;});
   player.start();
  } catch(Exception e){stopForeground(true);stopSelf(startId);}
  return START_NOT_STICKY;
 }
 @Override public void onDestroy(){if(player!=null){if(player.isPlaying())player.stop();player.release();player=null;}stopForeground(true);super.onDestroy();}
 @Override public android.os.IBinder onBind(Intent i){return null;}
}
''',encoding="utf-8")
manifest=root/"AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8")
for perm in ['android.permission.RECEIVE_BOOT_COMPLETED','android.permission.FOREGROUND_SERVICE','android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK']:
 if perm not in s:s=s.replace('    <application',f'    <uses-permission android:name="{perm}" />\n    <application',1)
if 'AdhanPlaybackService' not in s:
 s=s.replace('    </application>','''        <service android:name=".AdhanPlaybackService" android:exported="false" android:foregroundServiceType="mediaPlayback" />
        <receiver android:name=".PrayerAlarmReceiver" android:enabled="true" android:exported="false" />
        <receiver android:name=".PrayerBootReceiver" android:enabled="true" android:exported="true">
            <intent-filter><action android:name="android.intent.action.BOOT_COMPLETED" /></intent-filter>
        </receiver>
    </application>''')
manifest.write_text(s,encoding="utf-8")
main=java/"MainActivity.java"
ms=main.read_text(encoding="utf-8")
if "PrayerAlarmPlugin.class" not in ms:
 ms=ms.replace("public class MainActivity extends BridgeActivity {","public class MainActivity extends BridgeActivity {\n    @Override\n    public void onCreate(android.os.Bundle savedInstanceState) {\n        registerPlugin(PrayerAlarmPlugin.class);\n        super.onCreate(savedInstanceState);\n    }")
main.write_text(ms,encoding="utf-8")
raw=Path("android/app/src/main/res/raw");raw.mkdir(parents=True,exist_ok=True)
sources={
 "adhan_default.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Beautiful_adhan.ogg",
 "adhan_madinah.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/33937_ejaz215_call-to-prayer-from-the-prophet-s-mo.ogg",
 "adhan_general2.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Muslim_calling_to_prayer.ogg",
}
mecca_webm=raw/"adhan_mecca.webm"
subprocess.run(["curl","-fL","https://commons.wikimedia.org/wiki/Special:Redirect/file/Adhan,_Great_Mosque_of_Mecca_-_Jan_21,_2013.webm","-o",str(mecca_webm)],check=True)
subprocess.run(["ffmpeg","-y","-i",str(mecca_webm),"-vn","-acodec","libvorbis","-q:a","5",str(raw/"adhan_mecca.ogg")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
mecca_data=(raw/"adhan_mecca.ogg").read_bytes()
if len(mecca_data)<10000 or not mecca_data.startswith(b"OggS"):
 raise SystemExit("Mecca adhan conversion failed OGG validation")
for filename,url in sources.items():
 target=raw/filename
 subprocess.run(["curl","-fL",url,"-o",str(target)],check=True)
 data=target.read_bytes()
 if len(data)<10000 or not data.startswith(b"OggS"):
  raise SystemExit("Downloaded audio failed OGG validation: "+filename)
print("Native prayer alarm, foreground audio service, reboot restore, and three licensed OGG choices installed.")
