// Minimal client glue on top of HTMX.
(function () {
  // Debounce search input — HTMX's `delay` modifier already covers most
  // of this, but as a belt-and-suspenders measure throttle rapid changes.
  let timer;
  document.addEventListener("input", (event) => {
    if (event.target && event.target.matches('input[type="search"][name="q"]')) {
      clearTimeout(timer);
      timer = setTimeout(() => {
        event.target.form && event.target.form.requestSubmit &&
          event.target.form.requestSubmit();
      }, 250);
    }
  });
})();
