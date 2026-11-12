from pathlib import Path
import re, subprocess
root=Path("android/app/src/main")
java=root/"java/org/zadalkhair/app"
java.mkdir(parents=True,exist_ok=True)
(java/"PrayerAlarmPlugin.java").write_text(r'''package org.zadalkhair.app;
import android.app.AlarmManager;
import android.content.Context;
import android.os.Build;
import android.content.Intent;
import android.net.Uri;
import android.provider.Settings;
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
   String sound=call.getString("sound","syria");
   if(!"default".equals(sound)&&!"mecca".equals(sound)&&!"madinah".equals(sound)&&!"general2".equals(sound)&&!"tunisia".equals(sound)&&!"morocco".equals(sound)&&!"syria".equals(sound))sound="syria";
   String timezone=call.getString("timezone","Africa/Tunis");
   getContext().getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).edit().putString("sound",sound).putString("timezone",timezone).apply();
   PrayerAlarmReceiver.scheduleAll(getContext(),arr,timezone);
   call.resolve();
  } catch(Exception e) { call.reject("تعذّر ضبط أوقات الأذان: "+e.getMessage()); }
 }
 @PluginMethod public void checkExactAlarmPermission(PluginCall call) {
  AlarmManager manager=(AlarmManager)getContext().getSystemService(Context.ALARM_SERVICE);
  boolean granted=Build.VERSION.SDK_INT<31 || (manager!=null && manager.canScheduleExactAlarms());
  JSObject result=new JSObject();
  result.put("granted",granted);
  call.resolve(result);
 }
 @PluginMethod public void openExactAlarmSettings(PluginCall call) {
  try {
   if(Build.VERSION.SDK_INT>=31) {
    Intent intent=new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,Uri.parse("package:"+getContext().getPackageName()));
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    getContext().startActivity(intent);
   }
   call.resolve();
  } catch(Exception e) { call.reject("تعذّر فتح إعداد المنبّهات الدقيقة: "+e.getMessage()); }
 }
 @PluginMethod public void cancel(PluginCall call) {
  getContext().getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).edit().remove("times").remove("timezone").apply();
  PrayerAlarmReceiver.cancelAll(getContext());
  call.resolve();
 }
}
''',encoding="utf-8")
(java/"WelcomeVoicePlugin.java").write_text(r'''package org.zadalkhair.app;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import java.util.Locale;
import com.getcapacitor.*;
import com.getcapacitor.annotation.*;
@CapacitorPlugin(name="WelcomeVoice")
public class WelcomeVoicePlugin extends Plugin {
 private TextToSpeech tts;
 private boolean ready=false;
 @PluginMethod public void speak(PluginCall call) {
  if(tts==null) {
   tts=new TextToSpeech(getContext(),status->{
    if(status==TextToSpeech.SUCCESS) {
     int lang=tts.setLanguage(new Locale("ar"));
     ready=lang!=TextToSpeech.LANG_MISSING_DATA && lang!=TextToSpeech.LANG_NOT_SUPPORTED;
     if(ready) speakNow(call); else call.reject("Arabic speech voice is not installed on this phone. Install Arabic voice data in Android Text-to-Speech settings.");
    } else call.reject("Android speech engine is unavailable.");
   });
  } else if(ready) speakNow(call);
  else call.reject("Arabic speech voice is not ready.");
 }
 private void speakNow(PluginCall call) {
  tts.setSpeechRate(0.88f);
  tts.setPitch(0.94f);
  tts.speak("اذكر الله",TextToSpeech.QUEUE_FLUSH,null,"zad-welcome-1");
  tts.speak("وصلِّ على النبي محمد صلى الله عليه وسلم",TextToSpeech.QUEUE_ADD,null,"zad-welcome-2");
  call.resolve();
 }
 @Override protected void handleOnDestroy(){if(tts!=null){tts.stop();tts.shutdown();tts=null;}super.handleOnDestroy();}
}
''',encoding="utf-8")
(java/"PrayerAlarmReceiver.java").write_text(r'''package org.zadalkhair.app;
import android.app.*;
import android.content.*;
import android.os.Build;
import org.json.*;
import java.util.Calendar;
import java.util.TimeZone;
public class PrayerAlarmReceiver extends BroadcastReceiver {
 static final int BASE=82000;
 static PendingIntent pending(Context c,int id,int h,int m,String timezone) {
  Intent i=new Intent(c,PrayerAlarmReceiver.class).putExtra("hour",h).putExtra("minute",m).putExtra("alarmId",id).putExtra("timezone",timezone);
  return PendingIntent.getBroadcast(c,BASE+id,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
 }
 static void set(Context c,int id,int h,int m,String timezone) {
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  if(am==null)return;
  Calendar at=Calendar.getInstance(TimeZone.getTimeZone(timezone)); at.set(Calendar.HOUR_OF_DAY,h); at.set(Calendar.MINUTE,m); at.set(Calendar.SECOND,0); at.set(Calendar.MILLISECOND,0);
  if(at.getTimeInMillis()<=System.currentTimeMillis())at.add(Calendar.DAY_OF_YEAR,1);
  long when=at.getTimeInMillis();
  PendingIntent pi=pending(c,id,h,m,timezone);
  if(Build.VERSION.SDK_INT>=23)am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,when,pi);
  else am.setExact(AlarmManager.RTC_WAKEUP,when,pi);
 }
 static void scheduleAll(Context c,JSONArray a,String timezone) throws Exception {
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  if(Build.VERSION.SDK_INT>=31 && am!=null && !am.canScheduleExactAlarms())throw new IllegalStateException("فعّل إذن المنبّهات الدقيقة من إعدادات الهاتف");
  for(int i=0;i<a.length();i++){
   JSONObject o=a.getJSONObject(i);
   int hour=o.getInt("hour"),minute=o.getInt("minute");
   if(hour<0||hour>23||minute<0||minute>59)throw new IllegalArgumentException("وقت صلاة غير صالح");
  }
  cancelAll(c);
  for(int i=0;i<a.length();i++){JSONObject o=a.getJSONObject(i);set(c,i,o.getInt("hour"),o.getInt("minute"),timezone);}
 }
 static void cancelAll(Context c) {
  AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
  for(int i=0;i<5;i++){PendingIntent pi=pending(c,i,0,0,"Africa/Tunis");if(am!=null)am.cancel(pi);pi.cancel();}
 }
 @Override public void onReceive(Context c,Intent i) {
  int h=i.getIntExtra("hour",-1),m=i.getIntExtra("minute",-1),id=i.getIntExtra("alarmId",-1);
  String timezone=i.getStringExtra("timezone");if(timezone==null)timezone="Africa/Tunis";
  if(h<0||m<0)return;
  set(c,id,h,m,timezone);
  Intent service=new Intent(c,AdhanPlaybackService.class);
  if(Build.VERSION.SDK_INT>=26)c.startForegroundService(service);else c.startService(service);
 }
 static void restore(Context c) {
  try {
   String s=c.getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).getString("times","[]");
   String timezone=c.getSharedPreferences("zad_prayer_alarms",Context.MODE_PRIVATE).getString("timezone","Africa/Tunis");
   scheduleAll(c,new JSONArray(s),timezone);
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
   String selected=getSharedPreferences("zad_prayer_alarms",MODE_PRIVATE).getString("sound","syria");
   int audio=R.raw.adhan_syria;
   if("default".equals(selected))audio=R.raw.adhan_default;
   else if("mecca".equals(selected))audio=R.raw.adhan_mecca;
   else if("madinah".equals(selected))audio=R.raw.adhan_madinah;
   else if("general2".equals(selected))audio=R.raw.adhan_general2;
   else if("tunisia".equals(selected))audio=R.raw.adhan_tunisia;
   else if("morocco".equals(selected))audio=R.raw.adhan_morocco;
   else if("syria".equals(selected))audio=R.raw.adhan_syria;
   player=MediaPlayer.create(this,audio);
   if(player==null){stopSelf(startId);return START_NOT_STICKY;}
   player.setWakeMode(this,PowerManager.PARTIAL_WAKE_LOCK);
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
for perm in ['android.permission.RECEIVE_BOOT_COMPLETED','android.permission.WAKE_LOCK','android.permission.FOREGROUND_SERVICE','android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK','android.permission.SCHEDULE_EXACT_ALARM','android.permission.POST_NOTIFICATIONS']:
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
    insertion = """public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(android.os.Bundle savedInstanceState) {
        registerPlugin(PrayerAlarmPlugin.class);
        registerPlugin(WelcomeVoicePlugin.class);
        super.onCreate(savedInstanceState);
    }"""
    ms=ms.replace("public class MainActivity extends BridgeActivity {", insertion)
main.write_text(ms,encoding="utf-8")
raw=Path("android/app/src/main/res/raw");raw.mkdir(parents=True,exist_ok=True)
sources={
 "adhan_default.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Beautiful_adhan.ogg",
 "adhan_madinah.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/33937_ejaz215_call-to-prayer-from-the-prophet-s-mo.ogg",
 "adhan_general2.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Muslim_calling_to_prayer.ogg",
 "adhan_tunisia.ogg":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Oraci%C3%B3n_Al-Azzan.ogg",
 "adhan_syria.mp3":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Call_to_prayer_by_Sabah_Fakhry.mp3",
}
mecca_webm=raw/"adhan_mecca.webm"
subprocess.run(["curl","-fL","--retry","5","--retry-all-errors","--retry-delay","2","--connect-timeout","20","https://commons.wikimedia.org/wiki/Special:Redirect/file/Adhan,_Great_Mosque_of_Mecca_-_Jan_21,_2013.webm","-o",str(mecca_webm)],check=True)
subprocess.run(["ffmpeg","-y","-i",str(mecca_webm),"-vn","-acodec","libvorbis","-q:a","5",str(raw/"adhan_mecca.ogg")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
mecca_webm.unlink()
mecca_data=(raw/"adhan_mecca.ogg").read_bytes()
if len(mecca_data)<10000 or not mecca_data.startswith(b"OggS"):
 raise SystemExit("Mecca adhan conversion failed OGG validation")
for filename,url in sources.items():
 target=raw/filename
 subprocess.run(["curl","-fL","--retry","5","--retry-all-errors","--retry-delay","2","--connect-timeout","20",url,"-o",str(target)],check=True)
 data=target.read_bytes()
 if filename.endswith(".ogg") and (len(data)<10000 or not data.startswith(b"OggS")):
  raise SystemExit("Downloaded audio failed OGG validation: "+filename)
syria_mp3=raw/"adhan_syria.mp3"
subprocess.run(["ffmpeg","-y","-i",str(syria_mp3),"-vn","-acodec","libvorbis","-q:a","5",str(raw/"adhan_syria.ogg")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
syria_mp3.unlink()
syria_mp3=raw/"adhan_syria.mp3"
subprocess.run(["curl","-fL","--retry","5","--retry-all-errors","--retry-delay","2","--connect-timeout","20","https://commons.wikimedia.org/wiki/Special:Redirect/file/Call_to_prayer_by_Sabah_Fakhry.mp3","-o",str(syria_mp3)],check=True)
subprocess.run(["ffmpeg","-y","-i",str(syria_mp3),"-vn","-acodec","libvorbis","-q:a","5",str(raw/"adhan_syria.ogg")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
syria_mp3.unlink()
morocco_wav=raw/"adhan_morocco.wav"
subprocess.run(["curl","-fL","--retry","5","--retry-all-errors","--retry-delay","2","--connect-timeout","20","https://commons.wikimedia.org/wiki/Special:Redirect/file/Llamada_a_oraci%C3%B3n_Mezquita_Hassan_II.wav","-o",str(morocco_wav)],check=True)
subprocess.run(["ffmpeg","-y","-i",str(morocco_wav),"-vn","-acodec","libvorbis","-q:a","5",str(raw/"adhan_morocco.ogg")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
morocco_wav.unlink()
for name in ("adhan_tunisia.ogg","adhan_syria.ogg","adhan_morocco.ogg"):
 data=(raw/name).read_bytes()
 if len(data)<10000 or not data.startswith(b"OggS"):
  raise SystemExit("Downloaded or converted audio failed OGG validation: "+name)
print("Native prayer alarm, foreground audio service, reboot restore, timezone-aware scheduling, and seven licensed adhan choices installed.")
