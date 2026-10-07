(() => {
  const carousels = document.querySelectorAll("[data-carousel]");

  carousels.forEach((carousel) => {
    const slides = [...carousel.querySelectorAll("[data-carousel-slide]")];
    const indicators = [...carousel.querySelectorAll("[data-carousel-indicator]")];
    const previous = carousel.querySelector("[data-carousel-previous]");
    const next = carousel.querySelector("[data-carousel-next]");
    if (slides.length < 2) return;

    let current = 0;
    let timer;
    let pointerStart = null;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const show = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
      });
      indicators.forEach((indicator, indicatorIndex) => {
        const active = indicatorIndex === current;
        indicator.classList.toggle("is-active", active);
        indicator.setAttribute("aria-current", active ? "true" : "false");
      });
    };

    const stop = () => window.clearInterval(timer);
    const start = () => {
      stop();
      if (!reducedMotion) timer = window.setInterval(() => show(current + 1), 6000);
    };

    previous?.addEventListener("click", () => { show(current - 1); start(); });
    next?.addEventListener("click", () => { show(current + 1); start(); });
    indicators.forEach((indicator) => {
      indicator.addEventListener("click", () => {
        show(Number(indicator.dataset.carouselIndicator));
        start();
      });
    });
    carousel.addEventListener("mouseenter", stop);
    carousel.addEventListener("mouseleave", start);
    carousel.addEventListener("focusin", stop);
    carousel.addEventListener("focusout", start);
    carousel.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") show(current - 1);
      if (event.key === "ArrowRight") show(current + 1);
    });
    carousel.addEventListener("pointerdown", (event) => { pointerStart = event.clientX; });
    carousel.addEventListener("pointerup", (event) => {
      if (pointerStart === null) return;
      const distance = event.clientX - pointerStart;
      pointerStart = null;
      if (Math.abs(distance) > 45) show(current + (distance < 0 ? 1 : -1));
      start();
    });
    document.addEventListener("visibilitychange", () => document.hidden ? stop() : start());
    start();
  });
})();
