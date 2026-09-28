/* Service worker del curso: el material ya visto queda guardado para estudiar sin conexión. */
const CACHE = "aprendehebreo-v1";
const CORE = ["./", "index.html", "styles.css", "app.js", "api.html", "manifest.webmanifest",
              "icon.svg", "v1/index.json", "v1/alefbet.json", "v1/niqqud.json",
              "v1/lessons/index.json", "v1/vocab/top100.json", "v1/reading/index.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) =>
    Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (url.pathname.includes("/v1/")) {                       // material: caché primero
    e.respondWith(caches.open(CACHE).then((c) => c.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) c.put(req, res.clone());
      return res;
    }))));
    return;
  }
  e.respondWith(fetch(req).then((res) => {
    if (res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()));
    return res;
  }).catch(() => caches.match(req).then((hit) => hit || caches.match("index.html"))));
});
