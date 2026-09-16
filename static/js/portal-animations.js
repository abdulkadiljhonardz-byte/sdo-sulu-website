(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) return;

  const revealGroups = [
    ".home-service-grid > *",
    ".home-section-title",
    ".latest-records",
    ".service-directory",
    ".resource-list",
    ".vacancy-list",
    ".editorial-card",
    ".clean-announcement",
    ".division-overview",
    ".repository-header",
    ".repository-search",
    ".repository-table-wrap",
    ".page-main > h1",
    ".page-main > form",
    ".page-main > table",
  ];

  const targets = document.querySelectorAll(revealGroups.join(","));
  if (!("IntersectionObserver" in window)) return;

  document.documentElement.classList.add("motion-ready");
  targets.forEach((element, index) => {
    element.classList.add("reveal-target");
    element.style.setProperty("--reveal-delay", `${(index % 3) * 70}ms`);
  });

  const animateCount = (element) => {
    if (element.dataset.counted === "true") return;
    element.dataset.counted = "true";
    const target = Number.parseInt(element.dataset.count || "0", 10);
    if (!Number.isFinite(target) || target < 1) return;
    const duration = 900;
    const started = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(target * eased).toLocaleString();
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        entry.target.querySelectorAll("[data-count]").forEach(animateCount);
        if (entry.target.matches("[data-count]")) animateCount(entry.target);
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -35px" },
  );

  targets.forEach((element) => observer.observe(element));
  document.querySelectorAll("[data-count]").forEach((element) => observer.observe(element));

  const masthead = document.querySelector(".home-masthead");
  if (masthead) {
    let ticking = false;
    masthead.addEventListener("pointermove", (event) => {
      if (window.innerWidth < 900 || ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const rect = masthead.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width - 0.5) * 8;
        const y = ((event.clientY - rect.top) / rect.height - 0.5) * 8;
        masthead.style.setProperty("--pointer-x", `${x}px`);
        masthead.style.setProperty("--pointer-y", `${y}px`);
        ticking = false;
      });
    });
    masthead.addEventListener("pointerleave", () => {
      masthead.style.setProperty("--pointer-x", "0px");
      masthead.style.setProperty("--pointer-y", "0px");
    });
  }
})();
