// Registers the service worker and runs the "Turn on notifications" flow on the settings page.
(function () {
  // One tap per submit: buttons that call the model show a loading label and can't be pressed twice.
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (form.dataset.busy) { event.preventDefault(); return; }
    form.dataset.busy = "1";
    const btn = event.submitter || form.querySelector("button");
    if (btn && btn.dataset.loading) {
      btn.textContent = btn.dataset.loading;
      btn.classList.add("is-loading");
      btn.setAttribute("aria-busy", "true");
      setTimeout(() => { btn.disabled = true; }, 0);
    }
    // Pages restored from the back/forward cache must be usable again.
    window.addEventListener("pageshow", () => { delete form.dataset.busy; }, { once: true });
  });

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js", { scope: "/" });

  const enable = document.getElementById("enable-push");
  if (!enable) return;
  const test = document.getElementById("test-push");
  const status = document.getElementById("push-status");
  const guide = document.querySelector(".ios-guide");
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  const say = (t) => { status.textContent = t; };

  if (isIOS && !standalone) {
    guide.hidden = false;
    enable.hidden = true;
    return;
  }
  if (!("PushManager" in window) || !("Notification" in window)) {
    enable.hidden = true;
    say("This browser can't receive notifications. Try Chrome on Android or the home-screen app on iPhone.");
    return;
  }
  if (Notification.permission === "granted") { enable.textContent = "Notifications are on"; test.hidden = false; }

  const b64ToBytes = (b64) => {
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
  };

  enable.addEventListener("click", async () => {
    try {
      const { key } = await (await fetch("/vapid-public-key")).json();
      if (!key) { say("Notifications aren't set up on this server yet."); return; }
      if ((await Notification.requestPermission()) !== "granted") {
        say("Notifications are blocked. Allow them in your browser settings, then try again.");
        return;
      }
      const reg = await navigator.serviceWorker.ready;
      const sub = (await reg.pushManager.getSubscription()) ||
        (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) }));
      const r = await fetch("/push/subscribe", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(sub),
      });
      if (!r.ok) throw new Error(r.status);
      enable.textContent = "Notifications are on";
      test.hidden = false;
      say("You'll get one nudge at 09:00 when someone is due.");
    } catch (e) {
      say("Couldn't turn on notifications (" + e.message + "). Try again in a moment.");
    }
  });

  test.addEventListener("click", async () => {
    try {
      const r = await fetch("/push/test", { method: "POST" });
      const { sent, failed } = await r.json();
      if (sent) say("Test sent. Check your notifications.");
      else if (failed) say("The push service didn't answer. Try again in a minute.");
      else say("No device is subscribed yet. Turn notifications on first.");
    } catch (e) {
      say("Couldn't send the test (" + e.message + "). Try again in a minute.");
    }
  });
})();
