/* Demo chat widget ("HACKED" version for the live demo): same as clean, plus a red warning banner. Still harmless. */
(function () {
  var base = document.currentScript.src.replace(/[^/]+$/, "");
  function start() {
    var b = document.createElement("div");
    b.textContent = "Chat with us";
    b.style.cssText = "position:fixed;right:20px;bottom:20px;background:#1f6f5c;color:#fff;padding:12px 18px;border-radius:24px;font:600 14px system-ui;box-shadow:0 4px 12px rgba(0,0,0,.2);cursor:pointer;z-index:9999";
    document.body.appendChild(b);
    var w = document.createElement("div");
    w.textContent = "DEMO COMPROMISE: chat-widget.js was changed. This is a harmless test by the Blast Radius team.";
    w.style.cssText = "position:fixed;top:0;left:0;right:0;background:#c62828;color:#fff;padding:10px;text-align:center;font:700 14px system-ui;z-index:10000";
    document.body.appendChild(w);
    var h = document.createElement("script");
    h.src = base + "helper.js";
    document.head.appendChild(h);
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
})();
