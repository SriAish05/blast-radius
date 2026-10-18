/* Demo tag manager: loads two more scripts at runtime (they never appear in the page HTML). Harmless. */
(function () {
  var base = document.currentScript.src.replace(/[^/]+$/, "");
  ["analytics.js", "chat-widget.js"].forEach(function (file) {
    var s = document.createElement("script");
    s.src = base + file;
    document.head.appendChild(s);
  });
})();
