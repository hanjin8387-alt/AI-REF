const CACHE_NAME = "prometheus-shell-v4-20260213";
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/favicon.ico",
  "/favicon.webp",
  "/icons/icon-192.webp",
  "/icons/icon-512.webp",
  "/icons/maskable-icon-512.webp",
  "/icons/apple-touch-icon.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

async function cachePutIfValid(request, response) {
  if (!response || !response.ok) return response;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") return;

  const requestUrl = new URL(request.url);
  if (requestUrl.origin !== self.location.origin) return;

  const isStaticAsset = ["script", "style", "image", "font"].includes(request.destination);

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => cachePutIfValid(request, response))
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          return caches.match("/") || caches.match("/index.html");
        })
    );
    return;
  }

  if (isStaticAsset) {
    event.respondWith(
      fetch(request)
        .then((response) => cachePutIfValid(request, response))
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          throw new Error("Asset fetch failed");
        })
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => cachePutIfValid(request, response))
      .catch(() => caches.match(request))
  );
});

