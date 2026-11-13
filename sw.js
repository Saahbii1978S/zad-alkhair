const CACHE='zad-alkhair-shell-v66';
const QURAN_TEXT='zad-quran-text-v1';
const QURAN_AUDIO='zad-quran-audio-v2';
const FILES=['./','./index.html','./manifest.webmanifest','./icon.svg','./supabase-config.js','./native-notifications.js'];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>![CACHE,QURAN_TEXT,QURAN_AUDIO,'zad-quran-audio-v1'].includes(key)).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const request=event.request;
 if(request.method!=='GET')return;
 const url=new URL(request.url);
 if(url.origin===self.location.origin){
  if(request.mode==='navigate'){
   event.respondWith(fetch(request,{cache:'no-store'}).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put('./index.html',copy))}
    return response;
   }).catch(()=>caches.match('./index.html')));
   return;
  }
  event.respondWith(caches.match(request).then(hit=>hit||fetch(request).then(response=>{
   if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(request,copy))}
   return response;
  }).catch(()=>caches.match('./index.html'))));
  return;
 }
 if(url.hostname==='api.alquran.cloud'){
  event.respondWith(caches.open(QURAN_TEXT).then(async cache=>{
   const hit=await cache.match(request);if(hit)return hit;
   try{const response=await fetch(request);if(response.ok)await cache.put(request,response.clone());return response}
   catch(error){return new Response(JSON.stringify({code:503,status:'OFFLINE',data:null}),{status:503,headers:{'Content-Type':'application/json'}})}
  }));
  return;
 }
 if(url.hostname==='cdn.islamic.network'){
  event.respondWith(caches.open(QURAN_AUDIO).then(async cache=>{
   const hit=await cache.match(request);if(hit)return hit;
   const response=await fetch(request);
   if(response.ok||response.type==='opaque')await cache.put(request,response.clone());
   return response;
  }));
 }
});
