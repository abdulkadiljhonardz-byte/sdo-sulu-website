/* Local mobile navigation: no external CDN dependency. */
(function () {
  "use strict";

  function initialiseMobileNavigation() {
    var menuButton = document.querySelector(".menu-button");
    var navigation = document.getElementById("primary-menu");
    var header = document.querySelector("body > header");

    if (!menuButton || !navigation || !header) {
      return;
    }

    function setOpen(isOpen) {
      navigation.classList.toggle("is-open", isOpen);
      menuButton.classList.toggle("is-active", isOpen);
      menuButton.setAttribute("aria-expanded", String(isOpen));
    }

    menuButton.addEventListener("click", function () {
      setOpen(!navigation.classList.contains("is-open"));
    });

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
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialiseMobileNavigation);
  } else {
    initialiseMobileNavigation();
  }
}());
