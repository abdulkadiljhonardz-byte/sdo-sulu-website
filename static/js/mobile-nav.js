/* Local mobile navigation: no external CDN dependency. */
(function () {
  "use strict";

  function initialiseMobileNavigation() {
    var menuButton = document.querySelector(".menu-button");
    var navigation = document.getElementById("primary-menu");
    var header = document.querySelector("body > header");
    var backdrop = document.querySelector(".mobile-nav-backdrop");
    var submenuButtons = navigation
      ? navigation.querySelectorAll(".submenu-toggle")
      : [];

    if (!menuButton || !navigation || !header) {
      return;
    }

    function setOpen(isOpen) {
      navigation.classList.toggle("is-open", isOpen);
      menuButton.classList.toggle("is-active", isOpen);
      menuButton.setAttribute("aria-expanded", String(isOpen));
      document.body.classList.toggle("mobile-nav-open", isOpen);
      menuButton.querySelector(".sr-only").textContent = isOpen
        ? "Close navigation menu"
        : "Open navigation menu";
      if (!isOpen) {
        submenuButtons.forEach(function (button) {
          button.setAttribute("aria-expanded", "false");
          button.closest(".nav-dropdown").classList.remove("submenu-open");
        });
      }
    }

    menuButton.addEventListener("click", function () {
      setOpen(!navigation.classList.contains("is-open"));
    });

    submenuButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        var dropdown = button.closest(".nav-dropdown");
        var willOpen = !dropdown.classList.contains("submenu-open");

        submenuButtons.forEach(function (otherButton) {
          otherButton.setAttribute("aria-expanded", "false");
          otherButton.closest(".nav-dropdown").classList.remove("submenu-open");
        });
        dropdown.classList.toggle("submenu-open", willOpen);
        button.setAttribute("aria-expanded", String(willOpen));
      });
    });

    if (backdrop) {
      backdrop.addEventListener("click", function () {
        setOpen(false);
        menuButton.focus();
      });
    }

    navigation.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        setOpen(false);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && navigation.classList.contains("is-open")) {
        setOpen(false);
        menuButton.focus();
      }
    });

    document.addEventListener("click", function (event) {
      if (
        navigation.classList.contains("is-open") &&
        !header.contains(event.target)
      ) {
        setOpen(false);
      }
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 1000) {
        setOpen(false);
      }
    });

    setOpen(false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialiseMobileNavigation);
  } else {
    initialiseMobileNavigation();
  }
}());
