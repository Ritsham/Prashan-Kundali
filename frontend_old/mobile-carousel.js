/* ===== MOBILE ASTROLOGY CAROUSEL & SECTION DRAWER =====
   Provides swipeable section carousels and a secondary section navigation drawer
   for Kundali, Lagna, Match Making, and Prashna result views on small screens (<= 768px).

   Features:
   - Horizontal touch swipe with CSS smooth transitions & touch gesture handlers
   - Secondary section drawer (AstrologySectionDrawer) visually distinct from main drawer
   - Single-drawer rule (opening one closes the other)
   - Synchronizes active slide index with URL hash/query & section drawer items
   - Re-evaluates container bounds & triggers chart re-draws (via custom 'slide-activated' event)
   - Escape key & backdrop tap handling
*/

(function (global) {
  "use strict";

  function MobileAstrologyCarousel(config) {
    this.pageType = config.pageType || "kundali"; // kundali, lagna, matchmaking, prashna
    this.container = typeof config.container === "string" ? document.querySelector(config.container) : config.container;
    this.sections = config.sections || []; // Array of { id, title, element }
    this.currentIndex = config.initialIndex || 0;
    this.onSlideChange = config.onSlideChange || null;

    if (!this.container || this.sections.length === 0) return;

    this.init();
  }

  MobileAstrologyCarousel.prototype.init = function () {
    var hashIndex = this.indexFromHash();
    if (hashIndex >= 0) {
      this.currentIndex = hashIndex;
    } else if (this.pageType === "kundali") {
      var chartIndex = this.sections.findIndex(function (sec) { return sec.id === "lagna-chart"; });
      if (chartIndex >= 0) this.currentIndex = chartIndex;
    }
    this.buildMarkup();
    this.bindEvents();
    this.updateState(this.currentIndex, true);
    var self = this;
    setTimeout(function () {
      self.updateState(self.currentIndex, true);
    }, 350);
  };

  MobileAstrologyCarousel.prototype.indexFromHash = function () {
    var hash = (global.location && global.location.hash || "").replace(/^#section-/, "");
    if (!hash) return -1;
    return this.sections.findIndex(function (sec) { return sec.id === hash; });
  };

  MobileAstrologyCarousel.prototype.buildMarkup = function () {
    var self = this;

    // Check if controls already exist, if so clear/reuse
    var existingControls = this.container.querySelector(".mobile-carousel-controls");
    if (existingControls) existingControls.remove();
    var existingHeader = this.container.querySelector(".mobile-carousel-header-bar");
    if (existingHeader) existingHeader.remove();
    var existingViewport = this.container.querySelector(".mobile-carousel-viewport");
    if (existingViewport) existingViewport.remove();
    var existingSecDrawer = document.getElementById("mobile-section-drawer");
    if (existingSecDrawer) existingSecDrawer.remove();
    var existingSecScrim = document.getElementById("mobile-section-scrim");
    if (existingSecScrim) existingSecScrim.remove();

    // 1. Create Secondary Section Hamburger Button & Slide Header
    var headerControls = document.createElement("div");
    headerControls.className = "mobile-carousel-header-bar";
    headerControls.innerHTML =
      '<button type="button" id="mobile-sec-drawer-btn" class="mobile-sec-drawer-btn" aria-label="Open section navigation" aria-expanded="false" aria-controls="mobile-section-drawer">' +
        '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>' +
        '<span class="sec-btn-text">Sections</span>' +
      '</button>' +
      '<div class="mobile-carousel-title-wrap">' +
        '<span class="mobile-carousel-current-title" id="mobile-carousel-current-title"></span>' +
        '<span class="mobile-carousel-slide-counter" id="mobile-carousel-slide-counter"></span>' +
      '</div>';

    // 2. Create Secondary Drawer (AstrologySectionDrawer) + Scrim
    var scrim = document.createElement("div");
    scrim.id = "mobile-section-scrim";
    scrim.className = "mobile-section-scrim";
    scrim.setAttribute("aria-hidden", "true");

    var drawer = document.createElement("div");
    drawer.id = "mobile-section-drawer";
    drawer.className = "mobile-section-drawer";
    drawer.setAttribute("aria-hidden", "true");

    var drawerItemsHtml = this.sections.map(function (sec, idx) {
      return (
        '<button type="button" class="mobile-sec-item" data-slide-index="' + idx + '" data-section-id="' + sec.id + '">' +
          '<span class="sec-num">' + (idx + 1) + '</span>' +
          '<span class="sec-label">' + self.escapeHtml(sec.title) + '</span>' +
        '</button>'
      );
    }).join("");

    drawer.innerHTML =
      '<div class="mobile-sec-drawer-panel" role="dialog" aria-label="Astrology section menu">' +
        '<div class="mobile-sec-drawer-head">' +
          '<div>' +
            '<span class="sec-head-eyebrow">' + self.pageType.toUpperCase() + ' SECTIONS</span>' +
            '<h3>Select Section</h3>' +
          '</div>' +
          '<button type="button" id="mobile-sec-drawer-close" aria-label="Close section navigation">&times;</button>' +
        '</div>' +
        '<nav class="mobile-sec-nav-list">' + drawerItemsHtml + '</nav>' +
        '<div class="mobile-sec-drawer-foot">' +
          '<button type="button" id="mobile-sec-drawer-back" class="btn-sec-back">&larr; Return to view</button>' +
        '</div>' +
      '</div>';

    // 3. Build Carousel Track & Wrappers
    var carouselWrap = document.createElement("div");
    carouselWrap.className = "mobile-carousel-viewport";

    var carouselTrack = document.createElement("div");
    carouselTrack.className = "mobile-carousel-track";

    this.sections.forEach(function (sec, idx) {
      var slide = document.createElement("div");
      slide.className = "mobile-carousel-slide";
      slide.setAttribute("data-slide-index", idx);
      slide.setAttribute("data-section-id", sec.id);

      if (sec.element) {
        slide.appendChild(sec.element);
      }
      carouselTrack.appendChild(slide);
    });

    carouselWrap.appendChild(carouselTrack);

    // 4. Create Bottom Navigation Controls (Prev, Next, Dots)
    var navControls = document.createElement("div");
    navControls.className = "mobile-carousel-controls";

    var dotsHtml = this.sections.map(function (_, idx) {
      return '<button type="button" class="carousel-dot" data-slide-index="' + idx + '" aria-label="Go to slide ' + (idx + 1) + '"></button>';
    }).join("");

    navControls.innerHTML =
      '<button type="button" id="carousel-prev-btn" class="carousel-nav-btn prev-btn" aria-label="Previous slide">&larr; Prev</button>' +
      '<div class="carousel-dots-wrap">' + dotsHtml + '</div>' +
      '<button type="button" id="carousel-next-btn" class="carousel-nav-btn next-btn" aria-label="Next slide">Next &rarr;</button>';

    // Append to container
    this.container.appendChild(headerControls);
    this.container.appendChild(carouselWrap);
    this.container.appendChild(navControls);

    document.body.appendChild(scrim);
    document.body.appendChild(drawer);

    this.track = carouselTrack;
    this.drawer = drawer;
    this.scrim = scrim;
  };

  MobileAstrologyCarousel.prototype.bindEvents = function () {
    var self = this;

    // Hamburger button
    var openBtn = this.container.querySelector("#mobile-sec-drawer-btn");
    openBtn && openBtn.addEventListener("click", function () { self.openSectionDrawer(); });

    // Drawer close buttons
    var closeBtn = document.getElementById("mobile-sec-drawer-close");
    closeBtn && closeBtn.addEventListener("click", function () { self.closeSectionDrawer(); });

    var backBtn = document.getElementById("mobile-sec-drawer-back");
    backBtn && backBtn.addEventListener("click", function () { self.closeSectionDrawer(); });

    this.scrim && this.scrim.addEventListener("click", function () { self.closeSectionDrawer(); });

    // Section drawer item clicks
    var items = this.drawer.querySelectorAll(".mobile-sec-item");
    items.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var idx = parseInt(btn.getAttribute("data-slide-index"), 10);
        self.goToSlide(idx);
        self.closeSectionDrawer();
      });
    });

    // Prev / Next buttons
    var prevBtn = this.container.querySelector("#carousel-prev-btn");
    prevBtn && prevBtn.addEventListener("click", function () { self.prevSlide(); });

    var nextBtn = this.container.querySelector("#carousel-next-btn");
    nextBtn && nextBtn.addEventListener("click", function () { self.nextSlide(); });

    // Dot indicators
    var dots = this.container.querySelectorAll(".carousel-dot");
    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        var idx = parseInt(dot.getAttribute("data-slide-index"), 10);
        self.goToSlide(idx);
      });
    });

    // Touch Swipe Handling on Track
    var startX = 0, startY = 0, distX = 0, distY = 0, isSwiping = false;

    this.track.addEventListener("touchstart", function (e) {
      if (e.touches.length > 1) return;
      var touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;
      distX = 0;
      distY = 0;
      isSwiping = true;
    }, { passive: true });

    this.track.addEventListener("touchmove", function (e) {
      if (!isSwiping) return;
      var touch = e.touches[0];
      distX = touch.clientX - startX;
      distY = touch.clientY - startY;
    }, { passive: true });

    this.track.addEventListener("touchend", function () {
      if (!isSwiping) return;
      isSwiping = false;
      if (Math.abs(distX) > 40 && Math.abs(distY) < 60) {
        if (distX < 0) {
          self.nextSlide();
        } else {
          self.prevSlide();
        }
      }
    });

    // Keyboard Arrow Keys & Escape
    document.addEventListener("keydown", function (e) {
      if (self.drawer && self.drawer.classList.contains("open")) {
        if (e.key === "Escape") {
          self.closeSectionDrawer();
          return;
        }
      }
      var viewport = self.container.querySelector(".mobile-carousel-viewport");
      if (!viewport || window.innerWidth > 768) return;

      if (e.key === "ArrowLeft") {
        self.prevSlide();
      } else if (e.key === "ArrowRight") {
        self.nextSlide();
      }
    });
  };

  MobileAstrologyCarousel.prototype.openSectionDrawer = function () {
    // Single-drawer rule: Close main drawer if open
    if (window.closeMobileNavDrawer && typeof window.closeMobileNavDrawer === "function") {
      window.closeMobileNavDrawer();
    }
    var mainDrawer = document.getElementById("mobile-nav-drawer");
    var mainScrim = document.getElementById("mobile-drawer-scrim");
    if (mainDrawer && mainDrawer.classList.contains("open")) {
      mainDrawer.classList.remove("open");
      mainScrim && mainScrim.classList.remove("open");
      document.body.classList.remove("mdw-open-lock");
    }

    if (this.drawer && this.scrim) {
      this.drawer.classList.add("open");
      this.scrim.classList.add("open");
      this.drawer.setAttribute("aria-hidden", "false");
      document.body.classList.add("sec-drawer-open");
    }
  };

  MobileAstrologyCarousel.prototype.closeSectionDrawer = function () {
    if (this.drawer && this.scrim) {
      this.drawer.classList.remove("open");
      this.scrim.classList.remove("open");
      this.drawer.setAttribute("aria-hidden", "true");
      document.body.classList.remove("sec-drawer-open");
    }
  };

  MobileAstrologyCarousel.prototype.goToSlide = function (index, silent) {
    if (index < 0) index = 0;
    if (index >= this.sections.length) index = this.sections.length - 1;

    this.currentIndex = index;
    this.updateState(index, silent);
  };

  MobileAstrologyCarousel.prototype.prevSlide = function () {
    if (this.currentIndex > 0) {
      this.goToSlide(this.currentIndex - 1);
    }
  };

  MobileAstrologyCarousel.prototype.nextSlide = function () {
    if (this.currentIndex < this.sections.length - 1) {
      this.goToSlide(this.currentIndex + 1);
    }
  };

  MobileAstrologyCarousel.prototype.updateState = function (index, silent) {
    var currentSec = this.sections[index];
    if (!currentSec) return;

    this.sections.forEach(function (sec) {
      if (!sec.element) return;
      sec.element.classList.remove("hidden");
      sec.element.style.display = "";
    });

    if (this.pageType === "kundali") {
      var isKPSection = currentSec.id === "kp-tables";
      document.body.classList.toggle("show-kp", isKPSection);
      if (isKPSection) {
        document.body.classList.remove("show-planetary");
        var kpSection = currentSec.element && currentSec.element.querySelector("#kp-section");
        if (kpSection) {
          kpSection.classList.remove("hidden");
          kpSection.style.setProperty("display", "block", "important");
          kpSection.style.setProperty("visibility", "visible", "important");
          [
            ".kp-chart-panel",
            ".kp-details-panel",
            ".kp-significators-panel",
            ".kp-cusps-panel",
            ".table-wrap"
          ].forEach(function (selector) {
            kpSection.querySelectorAll(selector).forEach(function (node) {
              node.style.setProperty("display", "block", "important");
              node.style.setProperty("visibility", "visible", "important");
            });
          });
        }
      } else if (currentSec.id === "planet-positions") {
        document.body.classList.add("show-planetary");
      }
    }

    var chartCanvas = currentSec.element && currentSec.element.querySelector("#divisional-charts");
    if (chartCanvas) {
      var firstChart = chartCanvas.querySelector(".worksheet-item");
      if (firstChart && !chartCanvas.querySelector(".worksheet-item.is-mobile-active")) {
        firstChart.classList.add("is-mobile-active");
      }
    }

    if (this.track) {
      this.track.style.transform = "translateX(-" + (index * 100) + "%)";
    }

    var titleEl = this.container.querySelector("#mobile-carousel-current-title");
    if (titleEl) titleEl.textContent = currentSec.title;

    var counterEl = this.container.querySelector("#mobile-carousel-slide-counter");
    if (counterEl) counterEl.textContent = (index + 1) + " / " + this.sections.length;

    var dots = this.container.querySelectorAll(".carousel-dot");
    dots.forEach(function (dot, idx) {
      if (idx === index) dot.classList.add("active");
      else dot.classList.remove("active");
    });

    if (this.track) {
      Array.prototype.forEach.call(this.track.children, function (slide, idx) {
        if (idx === index) slide.classList.add("is-active");
        else slide.classList.remove("is-active");
      });
    }

    var prevBtn = this.container.querySelector("#carousel-prev-btn");
    if (prevBtn) prevBtn.disabled = (index === 0);

    var nextBtn = this.container.querySelector("#carousel-next-btn");
    if (nextBtn) nextBtn.disabled = (index === this.sections.length - 1);

    if (this.drawer) {
      var drawerItems = this.drawer.querySelectorAll(".mobile-sec-item");
      drawerItems.forEach(function (item, idx) {
        if (idx === index) item.classList.add("active");
        else item.classList.remove("active");
      });
    }

    try {
      if (history.replaceState) {
        history.replaceState(null, "", "#section-" + currentSec.id);
      }
    } catch (_e) {}

    var slideEl = this.track ? this.track.children[index] : null;
    if (slideEl) {
      var event = new CustomEvent("slide-activated", {
        bubbles: true,
        detail: { sectionId: currentSec.id, index: index, slideElement: slideEl }
      });
      slideEl.dispatchEvent(event);
    }

    setTimeout(function () {
      window.dispatchEvent(new Event("resize"));
    }, 250);

    if (!silent && typeof this.onSlideChange === "function") {
      this.onSlideChange(index, currentSec);
    }
  };

  MobileAstrologyCarousel.prototype.escapeHtml = function (str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  global.MobileAstrologyCarousel = MobileAstrologyCarousel;
})(typeof window !== "undefined" ? window : this);
