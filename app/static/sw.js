// OweMyGod service worker: shows the morning nudge and opens the list when tapped.
self.addEventListener("push", (event) => {
  let data = { title: "OweMyGod", body: "Someone is due today.", url: "/" };
  try { data = { ...data, ...event.data.json() }; } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body, icon: "/static/icon-192.png", badge: "/static/icon-192.png", data: { url: data.url },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) { if ("focus" in w) { w.navigate(url); return w.focus(); } }
    return clients.openWindow(url);
  }));
});
