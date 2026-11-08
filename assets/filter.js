/* Client-side filtering for the course list. Without JavaScript every course stays visible. */
(function () {
  "use strict";

  var q = document.getElementById("q");
  if (!q) return;

  var uni = document.getElementById("f-uni");
  var month = document.getElementById("f-month");
  var inperson = document.getElementById("f-inperson");
  var online = document.getElementById("f-online");
  var reset = document.getElementById("f-reset");
  var counter = document.getElementById("result-count");
  var empty = document.getElementById("no-results");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".uni-nav a[data-uni]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("section.uni"));
  var courses = Array.prototype.slice.call(document.querySelectorAll("li.course"));

  function fold(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  // Build the search index once, from the text already in the page.
  var index = courses.map(function (li) {
    return fold(li.textContent.replace(/\s+/g, " "));
  });

  function readUrl() {
    var p = new URLSearchParams(window.location.search);
    q.value = p.get("q") || "";
    uni.value = p.get("uni") || "";
    month.value = p.get("month") || "";
    inperson.checked = p.get("inperson") === "1";
    online.checked = p.get("online") === "1";
  }

  function writeUrl() {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set("q", q.value.trim());
    if (uni.value) p.set("uni", uni.value);
    if (month.value) p.set("month", month.value);
    if (inperson.checked) p.set("inperson", "1");
    if (online.checked) p.set("online", "1");
    var qs = p.toString();
    try {
      history.replaceState(null, "", window.location.pathname + (qs ? "?" + qs : "") + window.location.hash);
    } catch (e) { /* file:// or sandboxed: ignore */ }
  }

  function apply() {
    var terms = fold(q.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    var perUni = {};

    courses.forEach(function (li, i) {
      var ok = true;
      if (uni.value && li.dataset.uni !== uni.value) ok = false;
      if (ok && month.value) {
        var ms = (li.dataset.months || "").split(" ");
        if (ms.indexOf(month.value) === -1) ok = false;
      }
      if (ok && inperson.checked && li.dataset.inperson !== "yes") ok = false;
      if (ok && online.checked && li.dataset.online !== "yes") ok = false;
      if (ok) {
        for (var t = 0; t < terms.length; t++) {
          if (index[i].indexOf(terms[t]) === -1) { ok = false; break; }
        }
      }
      li.hidden = !ok;
      if (ok) {
        shown++;
        perUni[li.dataset.uni] = (perUni[li.dataset.uni] || 0) + 1;
      }
    });

    sections.forEach(function (s) { s.hidden = !perUni[s.dataset.uni]; });
    navLinks.forEach(function (a) { a.classList.toggle("dim", !perUni[a.dataset.uni]); });

    var filtered = terms.length || uni.value || month.value || inperson.checked || online.checked;
    counter.textContent = filtered
      ? "Showing " + shown + " of " + courses.length + " courses"
      : courses.length + " courses";
    empty.hidden = shown !== 0;
    writeUrl();
  }

  [q, uni, month, inperson, online].forEach(function (el) {
    el.addEventListener(el === q ? "input" : "change", apply);
  });
  reset.addEventListener("click", function () {
    // the native reset clears the controls; re-apply afterwards
    window.setTimeout(apply, 0);
  });

  // Open every <details> when printing, then restore.
  var opened = [];
  window.addEventListener("beforeprint", function () {
    opened = Array.prototype.slice.call(document.querySelectorAll("details:not([open])"));
    opened.forEach(function (d) { d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    opened.forEach(function (d) { d.open = false; });
    opened = [];
  });

  readUrl();
  apply();
})();
