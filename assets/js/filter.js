/* Free-text search over the course list. Without JavaScript every course stays visible. */
(function () {
  "use strict";

  var input = document.getElementById("q");
  if (!input) return;

  var counter = document.getElementById("result-count");
  var empty = document.getElementById("no-results");
  var sections = Array.prototype.slice.call(document.querySelectorAll("section.uni"));
  var courses = Array.prototype.slice.call(document.querySelectorAll("li.course"));
  var pills = Array.prototype.slice.call(document.querySelectorAll(".year-nav a[data-section]"));

  function fold(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  // Index built once from the text already on the page (including the collapsed syllabi).
  var index = courses.map(function (li) {
    return fold(li.textContent.replace(/\s+/g, " "));
  });

  function apply() {
    var terms = fold(input.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    var perSection = {};

    courses.forEach(function (li, i) {
      var ok = terms.every(function (t) { return index[i].indexOf(t) !== -1; });
      li.hidden = !ok;
      if (ok) {
        shown++;
        var id = li.closest("section.uni").id;
        perSection[id] = (perSection[id] || 0) + 1;
      }
    });

    sections.forEach(function (s) { s.hidden = !perSection[s.id]; });
    pills.forEach(function (a) { a.classList.toggle("dim", !perSection[a.dataset.section]); });

    counter.textContent = terms.length ? "Showing " + shown + " of " + courses.length : "";
    empty.hidden = shown !== 0;

    try {
      var q = input.value.trim();
      history.replaceState(null, "", location.pathname + (q ? "?q=" + encodeURIComponent(q) : "") + location.hash);
    } catch (e) { /* file:// or sandboxed: ignore */ }
  }

  input.addEventListener("input", apply);
  var initial = new URLSearchParams(location.search).get("q");
  if (initial) input.value = initial;
  apply();
})();
