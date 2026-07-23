/* ===== MOBILE NAV v3 =====
   Shared mobile header (hamburger + app name ONLY) + slide-in nav drawer,
   injected into every page so mobile UI is consistent site-wide instead of
   living only inside index.html. Replaces the old per-page "MOBILE DRAWER
   REDESIGN v2" markup that only existed on index.html.

   - Header: hamburger button (left) + app title (center-left). No share /
     download / edit / back icons (removed per bug report).
   - Drawer: real links only, based on files that actually exist in the repo:
       Home            -> /index.html
       Kundali         -> /index.html (scrolls to entry / result section)
       Match Making    -> /matchmaking.html
       Charts          -> /index.html (jumps to Charts tab of a result, if any)
       Predictions     -> /index.html (jumps to Interpretation tab of a result)
       Astro Community -> /astro-community
       About           -> /about.html
       Contact Us      -> /about-contact.html
     The signed-in account block opens Profile directly on mobile.
     Footer (bottom of drawer): Privacy Policy, Refund Policy, Disclaimer,
     Return Policy, Login/Logout.
     NOTE: no "Prashna" page exists as a standalone route (grep found no
     prashna*.html) - Prashna is a mode of the existing Kundali form on
     index.html (#prashna-form), so it is intentionally not a separate
     drawer link. Yoga/Dosha: no yoga/dosha feature found in app.js or
     chart-engine.js, so no such tab/link is fabricated anywhere.
*/
(function () {
  "use strict";

  var MOBILE_QUERY = "(max-width: 768px)";
  var isMounted = false;

  function isMobileViewport() {
    return window.matchMedia ? window.matchMedia(MOBILE_QUERY).matches : window.innerWidth <= 768;
  }

  function injectMarkup() {
    if (isMounted || document.getElementById("mobile-app-header")) return;
    var header = document.createElement("header");
    header.id = "mobile-app-header";
    header.className = "mobile-app-header";
    header.setAttribute("aria-label", "Section header");
    header.innerHTML =
      '<button type="button" id="mh-hamburger-btn" class="mh-icon-btn" aria-label="Open menu" aria-haspopup="true" aria-expanded="false" aria-controls="mobile-nav-drawer-v2">' +
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>' +
      '</button>' +
      '<h1 id="mh-title" class="mh-title">Shree Lakshmi Astro</h1>';

    var scrim = document.createElement("div");
    scrim.id = "mobile-drawer-scrim";
    scrim.className = "mobile-drawer-scrim";
    scrim.setAttribute("aria-hidden", "true");

    var drawer = document.createElement("div");
    drawer.id = "mobile-nav-drawer";
    drawer.className = "mobile-nav-drawer";
    drawer.setAttribute("aria-hidden", "true");
    drawer.innerHTML =
      '<div class="mobile-drawer-panel" id="mobile-nav-drawer-v2" role="dialog" aria-label="Navigation menu" aria-modal="true">' +
        '<div class="mobile-drawer-head">' +
          '<strong>Shree Lakshmi Astro</strong>' +
          '<button type="button" id="mobile-menu-close" aria-label="Close navigation menu">&times;</button>' +
        '</div>' +
        '<button type="button" class="mdw-profile" id="mdw-profile">' +
          '<div class="mdw-avatar" id="mdw-avatar">U</div>' +
          '<div class="mdw-profile-info">' +
            '<div class="mdw-profile-name" id="mdw-profile-name">Guest</div>' +
            '<div class="mdw-profile-sub" id="mdw-profile-sub">Sign in to save your charts</div>' +
            '<span class="mdw-plan-badge hidden" id="mdw-plan-badge"></span>' +
          '</div>' +
        '</button>' +
        '<nav class="mdw-links" aria-label="Primary">' +
          '<a href="/index.html" class="mobile-drawer-link" data-mobile-nav-link data-mdw-section="home">Home</a>' +
          '<a href="/consultation" class="mobile-drawer-link" data-mobile-nav-link data-mdw-section="consultant">Consultant</a>' +
          '<a href="/matchmaking.html" class="mobile-drawer-link" data-mobile-nav-link data-mdw-section="matchmaking">Match Making</a>' +
          '<a href="/astro-community" class="mobile-drawer-link mdw-community-alert" data-mobile-nav-link data-mdw-section="community">Astro Community <span>(Astrologers Only)</span></a>' +
          '<a href="/about.html" class="mobile-drawer-link" data-mobile-nav-link data-mdw-section="about">About</a>' +
          '<a href="/about-contact.html" class="mobile-drawer-link" data-mobile-nav-link data-mdw-section="contact">Contact Us</a>' +
        '</nav>' +
        '<div class="mdw-spacer"></div>' +
        '<div class="mdw-footer">' +
          '<a href="/privacy-policy.html" class="mobile-drawer-link mdw-footer-link">Privacy Policy</a>' +
          '<a href="/refund-policy.html" class="mobile-drawer-link mdw-footer-link">Refund Policy</a>' +
          '<a href="/disclaimer.html" class="mobile-drawer-link mdw-footer-link">Disclaimer</a>' +
          '<a href="/return-policy.html" class="mobile-drawer-link mdw-footer-link">Return Policy</a>' +
          '<button type="button" class="mobile-drawer-link mobile-login-link" id="mdw-login-btn" data-mobile-login>Login / Sign In</button>' +
          '<button type="button" class="mobile-drawer-link mdw-logout-link hidden" id="mdw-logout-btn">Sign Out</button>' +
        '</div>' +
      '</div>';

    document.body.prepend(drawer);
    document.body.prepend(scrim);
    document.body.prepend(header);
    isMounted = true;
  }

  function removeMarkup() {
    document.getElementById("mobile-app-header")?.remove();
    document.getElementById("mobile-drawer-scrim")?.remove();
    document.getElementById("mobile-nav-drawer")?.remove();
    document.body.classList.remove("mdw-open-lock");
    isMounted = false;
  }

  function wireBehaviour() {
    var hamburgerBtn = document.getElementById("mh-hamburger-btn");
    var drawer = document.getElementById("mobile-nav-drawer");
    var drawerPanel = document.getElementById("mobile-nav-drawer-v2");
    var drawerScrim = document.getElementById("mobile-drawer-scrim");
    var drawerClose = document.getElementById("mobile-menu-close");

    function openDrawer() {
      if (!drawer) return;
      // Single drawer rule: close section drawer if open
      var secDrawer = document.getElementById("mobile-section-drawer");
      var secScrim = document.getElementById("mobile-section-scrim");
      if (secDrawer && secDrawer.classList.contains("open")) {
        secDrawer.classList.remove("open");
        secScrim && secScrim.classList.remove("open");
        document.body.classList.remove("sec-drawer-open");
      }

      drawer.classList.add("open");
      drawerScrim && drawerScrim.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      hamburgerBtn && hamburgerBtn.setAttribute("aria-expanded", "true");
      document.body.classList.add("mdw-open-lock");
    }
    function closeDrawer() {
      if (!drawer) return;
      drawer.classList.remove("open");
      drawerScrim && drawerScrim.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      hamburgerBtn && hamburgerBtn.setAttribute("aria-expanded", "false");
      document.body.classList.remove("mdw-open-lock");
    }

    window.closeMobileNavDrawer = closeDrawer;
    window.openMobileNavDrawer = openDrawer;

    hamburgerBtn && hamburgerBtn.addEventListener("click", openDrawer);
    drawerClose && drawerClose.addEventListener("click", closeDrawer);
    drawerScrim && drawerScrim.addEventListener("click", closeDrawer);

    // Escape key handling for accessibility
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && drawer && drawer.classList.contains("open")) {
        closeDrawer();
      }
    });

    // Swipe-left-to-close on the drawer panel.
    (function initDrawerSwipe() {
      if (!drawerPanel) return;
      var startX = null, startY = null, tracking = false;
      drawerPanel.addEventListener("touchstart", function (e) {
        var t = e.touches[0];
        startX = t.clientX; startY = t.clientY; tracking = true;
      }, { passive: true });
      drawerPanel.addEventListener("touchmove", function (e) {
        if (!tracking) return;
        var t = e.touches[0];
        var dx = t.clientX - startX, dy = t.clientY - startY;
        if (dx < -60 && Math.abs(dy) < 40) { closeDrawer(); tracking = false; }
      }, { passive: true });
      drawerPanel.addEventListener("touchend", function () { tracking = false; });
    })();

    // Close drawer on any real nav link tap.
    drawerPanel && drawerPanel.querySelectorAll("a[data-mobile-nav-link]").forEach(function (a) {
      a.addEventListener("click", function () { closeDrawer(); });
    });

    // Login / Logout: reuse the existing auth modal + logout button if present
    // on this page (auth.js / auth-shared.js wire these ids up globally).
    document.getElementById("mdw-login-btn") && document.getElementById("mdw-login-btn").addEventListener("click", function () {
      closeDrawer();
      var loginBtn = document.getElementById("btn-login-header");
      loginBtn && loginBtn.click();
    });
    document.getElementById("mdw-logout-btn") && document.getElementById("mdw-logout-btn").addEventListener("click", function () {
      closeDrawer();
      var logoutBtn = document.getElementById("btn-logout");
      logoutBtn && logoutBtn.click();
    });
    document.getElementById("mdw-profile") && document.getElementById("mdw-profile").addEventListener("click", function () {
      closeDrawer();
      var logoutBtn = document.getElementById("mdw-logout-btn");
      if (logoutBtn && !logoutBtn.classList.contains("hidden")) {
        window.location.href = "/profile.html";
        return;
      }
      var loginBtn = document.getElementById("btn-login-header");
      loginBtn && loginBtn.click();
    });

    // Profile panel: populated from the real session via the "astro:authChanged"
    // event dispatched by auth.js (state.js AppState.setSession), same contract
    // used by the previous index.html-only drawer. No invented data.
    function renderDrawerProfile(session) {
      var nameEl = document.getElementById("mdw-profile-name");
      var subEl = document.getElementById("mdw-profile-sub");
      var avatarEl = document.getElementById("mdw-avatar");
      var badgeEl = document.getElementById("mdw-plan-badge");
      var loginBtn = document.getElementById("mdw-login-btn");
      var logoutBtn = document.getElementById("mdw-logout-btn");
      var user = session && session.user;
      if (user) {
        var fullName = (user.user_metadata && (user.user_metadata.full_name || user.user_metadata.name)) || "Member";
        var contact = user.email || user.phone || "";
        if (nameEl) nameEl.textContent = fullName;
        if (subEl) subEl.textContent = contact;
        if (avatarEl) avatarEl.textContent = (fullName || contact || "U").trim().charAt(0).toUpperCase() || "U";
        var plan = user.user_metadata && (user.user_metadata.plan || user.user_metadata.subscription_status);
        if (badgeEl) {
          if (plan) { badgeEl.textContent = plan; badgeEl.classList.remove("hidden"); }
          else badgeEl.classList.add("hidden");
        }
        loginBtn && loginBtn.classList.add("hidden");
        logoutBtn && logoutBtn.classList.remove("hidden");
      } else {
        if (nameEl) nameEl.textContent = "Guest";
        if (subEl) subEl.textContent = "Sign in to save your charts";
        if (avatarEl) avatarEl.textContent = "U";
        badgeEl && badgeEl.classList.add("hidden");
        loginBtn && loginBtn.classList.remove("hidden");
        logoutBtn && logoutBtn.classList.add("hidden");
      }
    }
    document.addEventListener("astro:authChanged", function (e) { renderDrawerProfile(e.detail); });
    var existingProfileMenu = document.querySelector("#profile-menu:not(.hidden)");
    renderDrawerProfile(existingProfileMenu ? { user: {} } : null);

    // Keep mobile title in sync with the active desktop result tab, if any
    // (index.html only; harmless no-op elsewhere).
    var mhTitle = document.getElementById("mh-title");
    var resultTabsNav = document.getElementById("result-tabs-nav");
    if (resultTabsNav && mhTitle) {
      var observer = new MutationObserver(function () {
        var activeBtn = resultTabsNav.querySelector(".tab-btn.active");
        if (activeBtn) mhTitle.textContent = activeBtn.textContent.trim();
      });
      observer.observe(resultTabsNav, { subtree: true, attributes: true, attributeFilter: ["class"] });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    function syncMobileNav() {
      if (isMobileViewport()) {
        if (!isMounted) {
          injectMarkup();
          wireBehaviour();
        }
      } else if (isMounted) {
        removeMarkup();
      }
    }

    syncMobileNav();

    if (window.matchMedia) {
      var mediaQuery = window.matchMedia(MOBILE_QUERY);
      if (mediaQuery.addEventListener) mediaQuery.addEventListener("change", syncMobileNav);
      else if (mediaQuery.addListener) mediaQuery.addListener(syncMobileNav);
    } else {
      window.addEventListener("resize", syncMobileNav);
    }
  });
})();
