(() => {
  const loader = document.getElementById("site-loader");
  if (!loader) return;

  document.body.classList.add("page-loading");
  const startedAt = performance.now();
  const minimumDisplay = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 150 : 700;

  const dismiss = () => {
    const remaining = Math.max(0, minimumDisplay - (performance.now() - startedAt));
    window.setTimeout(() => {
      loader.classList.add("is-hiding");
      document.body.classList.remove("page-loading");
      window.setTimeout(() => loader.remove(), 450);
    }, remaining);
  };

  if (document.readyState === "complete") dismiss();
  else window.addEventListener("load", dismiss, { once: true });

  window.setTimeout(dismiss, 3500);
})();
