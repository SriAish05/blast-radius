/* Demo chat widget (CLEAN version): shows a chat bubble and loads helper.js at runtime. Harmless. */
(function () {
  var base = document.currentScript.src.replace(/[^/]+$/, "");
  function start() {
    var b = document.createElement("div");
    b.textContent = "Chat with us";
    b.style.cssText = "position:fixed;right:20px;bottom:20px;background:#1f6f5c;color:#fff;padding:12px 18px;border-radius:24px;font:600 14px system-ui;box-shadow:0 4px 12px rgba(0,0,0,.2);cursor:pointer;z-index:9999";
    document.body.appendChild(b);
    
    var h = document.createElement("script");
    h.src = base + "helper.js";
    document.head.appendChild(h);
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
})();
