import { reactive, ref, onMounted, onUnmounted } from 'vue';

// Pricing / checkout URL patterns
const PRICING_PATTERNS = ['/pricing', '/plans', '/checkout', '/subscribe', '/upgrade', '/buy'];
const CHECKOUT_PATTERNS = ['/checkout', '/cart', '/order'];

// CTA text patterns — clicking these = purchase intent
const CTA_PATTERNS = /add.to.cart|buy.now|add.to.bag|get.started|start.free|subscribe|purchase|checkout|order.now|shop.now|sign.up|try.free|book.now|get.quote|contact.us|request.demo/i;

// High-signal events that flush immediately
const IMMEDIATE_FLUSH_EVENTS = new Set(['add_to_cart', 'rage_click', 'form_abandoned', 'exit_intent']);

// Commercial/price element selectors for IntersectionObserver
const PRICE_SELECTORS = [
  '.price', '.woocommerce-Price-amount', '[itemprop="price"]',
  '.product__price', '.price-item', '.entry-price',
  '[class*="price-amount"]', '[class*="product-price"]',
].join(', ');

// Add-to-cart selectors for WooCommerce / generic
const ATC_SELECTORS = [
  '.add_to_cart_button', '.single_add_to_cart_button',
  '[name="add-to-cart"]', '[data-product_id]',
].join(', ');

// ── UA helpers ────────────────────────────────────────────────────────────────
function parseDevice(ua) {
  if (/tablet|ipad|playbook|silk/i.test(ua)) return 'tablet';
  if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile|wpdesktop/i.test(ua)) return 'mobile';
  return 'desktop';
}
function parseOS(ua) {
  if (/windows nt/i.test(ua)) return 'Windows';
  if (/mac os x/i.test(ua) && !/iphone|ipad|ipod/i.test(ua)) return 'macOS';
  if (/iphone|ipad|ipod/i.test(ua)) return 'iOS';
  if (/android/i.test(ua)) return 'Android';
  if (/linux/i.test(ua)) return 'Linux';
  return 'Unknown';
}
function parseBrowser(ua) {
  if (/edg\//i.test(ua)) return 'Edge';
  if (/opr\//i.test(ua) || /opera/i.test(ua)) return 'Opera';
  if (/firefox/i.test(ua)) return 'Firefox';
  if (/chrome/i.test(ua)) return 'Chrome';
  if (/safari/i.test(ua)) return 'Safari';
  return 'Other';
}

// ── Returning visitor detection ───────────────────────────────────────────────
const RETURNING_KEY = '__cf_returning__';
function checkReturning() {
  const isReturning = !!localStorage.getItem(RETURNING_KEY);
  localStorage.setItem(RETURNING_KEY, '1');
  return isReturning;
}

// ── Privacy: respect Do Not Track ────────────────────────────────────────────
function isTrackingAllowed() {
  return navigator.doNotTrack !== '1' && window.doNotTrack !== '1';
}

export function useTracker() {
  // Bail silently if DNT is set — beacon still fires but with minimal data
  const trackingEnabled = isTrackingAllowed();

  const SESSION_KEY = '__cf_sid__';
  const sessionId = sessionStorage.getItem(SESSION_KEY) || (() => {
    const id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  })();

  // All queued events since last flush
  const events = [];
  // Track whether new events arrived since last periodic flush
  let eventsSinceLastFlush = 0;

  // ── Behavior matrix (sent with every beacon) ──────────────────────────────
  const behaviorMatrix = reactive({
    // Existing signals
    pagesViewed: [],
    timeOnSite: 0,
    hoverCount: 0,
    scrollDepth: 0,
    intentLevel: 'Casual Browser',
    pricingPageVisits: 0,
    exitIntentFired: false,

    // Scroll milestones
    scrollMilestones: [],        // [25, 50, 75, 90] — percentages reached

    // Click signals
    clickCount: 0,               // total clicks
    ctaClicks: 0,                // clicks on CTA buttons
    rageClicks: 0,               // rage-click instances

    // Form engagement
    formFocused: false,          // any input was focused
    formAbandoned: false,        // form started, then left without submit

    // Commercial signals
    addToCartClicks: 0,          // add-to-cart button clicks
    priceViews: 0,               // price elements that entered viewport
    copyEvents: 0,               // text copy events
    checkoutVisits: 0,           // checkout page visits

    // Content engagement
    videoPlays: 0,               // HTML5 video/audio play events
    fileDownloads: 0,            // PDF/ZIP/DOC link clicks

    // Session quality
    idleSeconds: 0,              // seconds with no mouse movement
    tabHiddenSeconds: 0,         // seconds tab was not visible
  });

  // Visitor metadata
  const visitorMeta = ref({
    device: parseDevice(navigator.userAgent),
    os: parseOS(navigator.userAgent),
    browser: parseBrowser(navigator.userAgent),
    referrer: document.referrer || null,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
    country: null,
    city: null,
    country_code: null,
    ip: null,
    is_returning: checkReturning(),
  });

  // Detailed page visit log with durations. Persisted to sessionStorage
  // so the list accumulates across full page reloads within the same
  // browser session — otherwise navigating between pages would reset it
  // and the bot would only see the last page when a trigger fires.
  const PV_STORAGE_KEY = `cf_pv_${sessionId}`;
  const _loadPersistedPageVisits = () => {
    try {
      const raw = sessionStorage.getItem(PV_STORAGE_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr.slice(-30) : [];
    } catch { return []; }
  };
  const _persistPageVisits = () => {
    try {
      sessionStorage.setItem(PV_STORAGE_KEY, JSON.stringify(pageVisits.value.slice(-30)));
    } catch {}
  };
  const pageVisits = ref(_loadPersistedPageVisits());
  let currentPageEntry = null;

  let startTime = Date.now();
  let timeInterval = null;
  let periodicFlushInterval = null;
  let nudgeTimeout = null;
  let nudgeFired = false;
  let onNudgeTriggered = () => {};

  const setNudgeCallback = (cb) => { onNudgeTriggered = cb; };

  // ── API helpers ───────────────────────────────────────────────────────────
  const getApiBase = () => {
    if (window.__CF_BACKEND_URL__) return window.__CF_BACKEND_URL__;
    const h = window.location.hostname;
    return (h === 'localhost' || h === '127.0.0.1') ? 'http://127.0.0.1:8000' : '';
  };

  const fireTrigger = (triggerType) => {
    const clientId = window.__CF_CLIENT_ID__;
    if (!clientId || !sessionId) return;
    fetch(`${getApiBase()}/api/chat/trigger/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, client_id: clientId, trigger_type: triggerType }),
    }).catch(() => {});
  };

  // ── Geo lookup ────────────────────────────────────────────────────────────
  const fetchGeo = async () => {
    try {
      const res = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(5000) });
      if (!res.ok) return;
      const data = await res.json();
      visitorMeta.value.country = data.country_name || null;
      visitorMeta.value.city = data.city || null;
      visitorMeta.value.country_code = data.country_code || null;
      visitorMeta.value.ip = data.ip || null;
    } catch {}
  };

  // ── Logging and flushing ──────────────────────────────────────────────────
  const logEvent = (type, data) => {
    events.push({ type, data, timestamp: Date.now() });
    eventsSinceLastFlush++;
  };

  const finalizeCurrentPage = () => {
    if (!currentPageEntry) return;
    const duration = Math.round((Date.now() - currentPageEntry.enteredAt) / 1000);
    pageVisits.value.push({
      url: currentPageEntry.url,
      title: currentPageEntry.title,
      duration_seconds: duration,
      visited_at: new Date(currentPageEntry.enteredAt).toISOString(),
    });
    _persistPageVisits();
    currentPageEntry = null;
  };

  const flushBeacon = (force = false) => {
    if (!force && eventsSinceLastFlush === 0) return;
    eventsSinceLastFlush = 0;

    // Finalize page but don't clear currentPageEntry (page still open)
    const snapshot = currentPageEntry ? [{
      url: currentPageEntry.url,
      title: currentPageEntry.title,
      duration_seconds: Math.round((Date.now() - currentPageEntry.enteredAt) / 1000),
      visited_at: new Date(currentPageEntry.enteredAt).toISOString(),
    }] : [];

    const url = `${getApiBase()}/api/analytics/beacon/`;
    const clientId = window.__CF_CLIENT_ID__;
    const payload = JSON.stringify({
      sessionId,
      clientId,
      behaviorMatrix,
      events: [...events],
      page_visits_snapshot: [...pageVisits.value, ...snapshot],
    });

    if (navigator.sendBeacon) {
      navigator.sendBeacon(url, payload);
    } else {
      fetch(url, { method: 'POST', body: payload, keepalive: true }).catch(() => {});
    }
    events.length = 0;
  };

  // Final flush — called on beforeunload / unmount
  const sendBeacon = () => {
    finalizeCurrentPage();
    flushBeacon(true);
  };

  // ── Page view tracking ────────────────────────────────────────────────────
  const trackPageView = () => {
    finalizeCurrentPage();
    const path = window.location.pathname;
    currentPageEntry = { url: path, title: document.title || path, enteredAt: Date.now() };
    behaviorMatrix.pagesViewed.push(path);
    logEvent('page_view', path);

    if (PRICING_PATTERNS.some(p => path.toLowerCase().includes(p))) {
      behaviorMatrix.pricingPageVisits++;
      logEvent('pricing_visit', path);
      if (behaviorMatrix.pricingPageVisits >= 2) {
        fireTrigger('pricing_hesitation');
      } else {
        setTimeout(() => {
          if (PRICING_PATTERNS.some(p => window.location.pathname.toLowerCase().includes(p))) {
            fireTrigger('pricing_hesitation');
          }
        }, 30000);
      }
    }

    if (CHECKOUT_PATTERNS.some(p => path.toLowerCase().includes(p))) {
      behaviorMatrix.checkoutVisits++;
      logEvent('checkout_visit', path);
      // Immediate flush — checkout visit is highest urgency signal
      flushBeacon(true);
    }
  };

  // ── Scroll tracking ───────────────────────────────────────────────────────
  const SCROLL_MILESTONES = [25, 50, 75, 90];

  const trackScroll = () => {
    let ticking = false;
    const handleScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const docH = Math.max(
          document.body.scrollHeight, document.documentElement.scrollHeight,
          document.body.offsetHeight, document.documentElement.offsetHeight,
        ) - window.innerHeight;
        if (docH <= 0) { ticking = false; return; }

        const depth = Math.round((window.scrollY / docH) * 100);
        if (depth > behaviorMatrix.scrollDepth) {
          behaviorMatrix.scrollDepth = depth;
        }

        for (const m of SCROLL_MILESTONES) {
          if (depth >= m && !behaviorMatrix.scrollMilestones.includes(m)) {
            behaviorMatrix.scrollMilestones.push(m);
            logEvent('scroll_milestone', m);
          }
        }

        // C7 — engagement trigger: scroll ≥50% + time ≥30s
        // QA report flagged the old 75% + 90s bar as way too high — most
        // visitors who would benefit from a nudge had already bounced by then.
        // Lowered to capture mid-funnel browsers who are exploring but not
        // yet ready to act. Backend cooldown (last_nudge_at 60s) still
        // prevents overlap with other triggers (proactive_open, afk_nudge).
        if (
          depth >= 50 &&
          behaviorMatrix.timeOnSite >= 30 &&
          !nudgeFired
        ) {
          nudgeFired = true;
          behaviorMatrix.intentLevel = 'High-Intent Lead';
          onNudgeTriggered();
          fireTrigger('deep_engagement');
        }

        ticking = false;
      });
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  };

  // ── Hover tracking ────────────────────────────────────────────────────────
  const trackHovers = () => {
    if (!trackingEnabled) return;
    document.querySelectorAll('button, a').forEach(el => {
      el.addEventListener('mouseenter', () => {
        behaviorMatrix.hoverCount++;
        logEvent('hover', el.innerText?.slice(0, 40) || el.id || el.tagName);
      });
    });
  };

  // ── Click tracking with rage-click detection ──────────────────────────────
  const trackClicks = () => {
    if (!trackingEnabled) return;

    // key → recent timestamps for rage detection
    const recentClicks = {};

    const handleClick = (e) => {
      const el = e.target.closest('button, a, [role="button"], input[type="submit"]') || e.target;
      const text = (el.innerText || el.value || el.alt || '').trim().slice(0, 60);
      const tag = el.tagName.toLowerCase();

      behaviorMatrix.clickCount++;
      logEvent('click', { tag, text: text.slice(0, 40), x: Math.round(e.clientX), y: Math.round(e.clientY) });

      // CTA detection
      if (CTA_PATTERNS.test(text) || el.matches(ATC_SELECTORS)) {
        const isATC = el.matches(ATC_SELECTORS) || /add.to.cart/i.test(text);
        if (isATC) {
          behaviorMatrix.addToCartClicks++;
          logEvent('add_to_cart', text);
          fireTrigger('add_to_cart_help');
          flushBeacon(true);
        } else {
          behaviorMatrix.ctaClicks++;
          logEvent('cta_click', text);
        }
      }

      // File download
      if (tag === 'a') {
        const href = el.getAttribute('href') || '';
        if (/\.(pdf|zip|docx?|xlsx?|pptx?|csv|mp4|mp3)(\?|$)/i.test(href)) {
          behaviorMatrix.fileDownloads++;
          logEvent('file_download', href.split('/').pop().slice(0, 40));
        }
      }

      // Rage-click detection: 3+ clicks in 1000ms on same rough position
      const key = `${Math.round(e.clientX / 20)}_${Math.round(e.clientY / 20)}`;
      if (!recentClicks[key]) recentClicks[key] = [];
      const now = Date.now();
      recentClicks[key] = recentClicks[key].filter(t => now - t < 1000);
      recentClicks[key].push(now);

      if (recentClicks[key].length >= 3) {
        recentClicks[key] = [];
        behaviorMatrix.rageClicks++;
        logEvent('rage_click', { x: Math.round(e.clientX), y: Math.round(e.clientY) });
        fireTrigger('rage_click_help');
        flushBeacon(true);
      }
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  };

  // ── Form engagement tracking ──────────────────────────────────────────────
  const trackForms = () => {
    if (!trackingEnabled) return;

    let lastFocusedValue = '';
    let formFocusAt = 0;

    const onFocusIn = (e) => {
      if (!e.target.matches('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select')) return;
      lastFocusedValue = e.target.value || '';
      formFocusAt = Date.now();
      if (!behaviorMatrix.formFocused) {
        behaviorMatrix.formFocused = true;
        logEvent('form_focus', e.target.name || e.target.type || 'field');
      }
    };

    const onFocusOut = (e) => {
      if (!e.target.matches('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select')) return;
      const dwellMs = Date.now() - formFocusAt;
      const hasValue = !!(e.target.value || '').trim();
      const hadValue = !!lastFocusedValue.trim();

      // Abandoned = dwelled ≥4s with no value entered, or typed something then cleared
      if (dwellMs >= 4000 && !hasValue && !hadValue) {
        behaviorMatrix.formAbandoned = true;
        logEvent('form_abandoned', e.target.name || e.target.type || 'field');
        fireTrigger('abandoned_form');
        flushBeacon(true);
      }
    };

    document.addEventListener('focusin', onFocusIn);
    document.addEventListener('focusout', onFocusOut);
    return () => {
      document.removeEventListener('focusin', onFocusIn);
      document.removeEventListener('focusout', onFocusOut);
    };
  };

  // ── Exit-intent detection ─────────────────────────────────────────────────
  // Fires when the visitor signals they're about to leave.
  //
  //   • Desktop  → cursor crosses top of viewport (`mouseleave` with clientY < 20)
  //   • Mobile   → `visibilitychange` to hidden, OR `pagehide` — both are
  //                the closest analogue to "I'm leaving" on touch devices.
  //                Touch devices never fire `mouseleave`, which is why this
  //                trigger never worked on phones before.
  //
  // Gates (same on both): time on site ≥ 10s, not already fired.
  const trackExitIntent = () => {
    const fireExitIntent = (source) => {
      if (behaviorMatrix.exitIntentFired) return;
      if (behaviorMatrix.timeOnSite < 10) return;
      behaviorMatrix.exitIntentFired = true;
      logEvent('exit_intent', `${window.location.pathname} (${source})`);
      fireTrigger('exit_intent');
      flushBeacon(true);
    };

    // Desktop path
    const handleMouseLeave = (e) => {
      if (e.clientY > 20) return;
      fireExitIntent('mouse');
    };
    document.addEventListener('mouseleave', handleMouseLeave);

    // Mobile path 1 — visitor backgrounded the tab / locked the screen /
    // hit the home button. This is what a mobile user does instead of
    // moving a cursor off the top of the screen.
    const handleVisibility = () => {
      if (document.hidden) fireExitIntent('visibility');
    };
    document.addEventListener('visibilitychange', handleVisibility);

    // Mobile path 2 — `pagehide` fires when the visitor actually navigates
    // away on iOS Safari (where `beforeunload` is unreliable). Same gate.
    const handlePageHide = () => fireExitIntent('pagehide');
    window.addEventListener('pagehide', handlePageHide);

    return () => {
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('pagehide', handlePageHide);
    };
  };

  // ── Tab visibility tracking ───────────────────────────────────────────────
  const trackTabVisibility = () => {
    let hiddenAt = null;
    const handleVisibility = () => {
      if (document.hidden) {
        hiddenAt = Date.now();
      } else if (hiddenAt) {
        behaviorMatrix.tabHiddenSeconds += Math.round((Date.now() - hiddenAt) / 1000);
        hiddenAt = null;
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  };

  // ── Activity-idle tracking ────────────────────────────────────────────────
  // Renamed conceptually from "mouse" idle to "activity" idle because mobile
  // users never fire `mousemove`. Before this fix, `lastMove` was set once on
  // init and never updated on mobile → every mobile session showed
  // perpetually idle, polluting the AFK trigger logic and pushing nudges
  // when the visitor was actually scrolling and reading.
  //
  // We now reset the activity timestamp on ANY of: mousemove, touchstart,
  // touchmove, scroll, keydown. That covers every reasonable definition of
  // "the visitor is still here" on both desktop and touch.
  const trackMouseIdle = () => {
    if (!trackingEnabled) return () => {};
    let lastMove = Date.now();
    let idleInterval = null;

    const markActive = () => { lastMove = Date.now(); };

    // Passive listeners so we never block native scroll on touch devices.
    document.addEventListener('mousemove',  markActive, { passive: true });
    document.addEventListener('touchstart', markActive, { passive: true });
    document.addEventListener('touchmove',  markActive, { passive: true });
    document.addEventListener('scroll',     markActive, { passive: true });
    document.addEventListener('keydown',    markActive, { passive: true });

    idleInterval = setInterval(() => {
      const idleSec = Math.round((Date.now() - lastMove) / 1000);
      if (idleSec >= 10) {
        // Count each 5s interval of idleness
        behaviorMatrix.idleSeconds = Math.min(behaviorMatrix.idleSeconds + 5, 3600);
      }
    }, 5000);

    return () => {
      document.removeEventListener('mousemove',  markActive);
      document.removeEventListener('touchstart', markActive);
      document.removeEventListener('touchmove',  markActive);
      document.removeEventListener('scroll',     markActive);
      document.removeEventListener('keydown',    markActive);
      clearInterval(idleInterval);
    };
  };

  // ── Price visibility (IntersectionObserver) ───────────────────────────────
  const trackPriceVisibility = () => {
    if (!trackingEnabled || !window.IntersectionObserver) return () => {};

    let priceObs = null;
    const seenPrices = new Set();

    setTimeout(() => {
      const priceEls = document.querySelectorAll(PRICE_SELECTORS);
      if (!priceEls.length) return;

      priceObs = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !seenPrices.has(entry.target)) {
            seenPrices.add(entry.target);
            behaviorMatrix.priceViews++;
            logEvent('price_view', entry.target.textContent?.trim().slice(0, 20));
          }
        }
      }, { threshold: 0.5 });

      priceEls.forEach(el => priceObs.observe(el));
    }, 1500);

    return () => { priceObs?.disconnect(); };
  };

  // ── Copy event tracking ───────────────────────────────────────────────────
  const trackCopyEvents = () => {
    if (!trackingEnabled) return () => {};
    const onCopy = () => {
      const sel = window.getSelection()?.toString().trim();
      if (!sel || sel.length < 3) return;
      behaviorMatrix.copyEvents++;
      logEvent('copy', sel.slice(0, 30));
    };
    document.addEventListener('copy', onCopy);
    return () => document.removeEventListener('copy', onCopy);
  };

  // ── Video/audio play tracking ─────────────────────────────────────────────
  const trackMedia = () => {
    const onPlay = (e) => {
      behaviorMatrix.videoPlays++;
      logEvent('media_play', e.target.src?.split('/').pop()?.slice(0, 40) || 'video');
    };
    document.addEventListener('play', onPlay, true);
    return () => document.removeEventListener('play', onPlay, true);
  };

  // ── Nudge evaluation ──────────────────────────────────────────────────────
  const evaluateAndTriggerNudge = () => {
    if (nudgeFired) return;
    if (behaviorMatrix.timeOnSite >= 30 || behaviorMatrix.scrollDepth >= 50) {
      nudgeFired = true;
      behaviorMatrix.intentLevel = 'High-Intent Lead';
      onNudgeTriggered();
    }
  };

  // Cleanup refs
  let cleanupFns = [];

  onMounted(() => {
    startTime = Date.now();
    trackPageView();
    fetchGeo();

    cleanupFns = [
      trackScroll(),
      trackClicks(),
      trackForms(),
      trackExitIntent(),
      trackTabVisibility(),
      trackMouseIdle(),
      trackPriceVisibility(),
      trackCopyEvents(),
      trackMedia(),
    ].filter(Boolean);

    setTimeout(trackHovers, 500);

    // Update time on site every 5s + evaluate nudge
    timeInterval = setInterval(() => {
      behaviorMatrix.timeOnSite = Math.round((Date.now() - startTime) / 1000);
      evaluateAndTriggerNudge();

      // high_intent_action trigger: intent EMA signals + sustained engagement
      if (
        behaviorMatrix.timeOnSite >= 120 &&
        (behaviorMatrix.ctaClicks >= 1 || behaviorMatrix.pricingPageVisits >= 1) &&
        !nudgeFired
      ) {
        nudgeFired = true;
        behaviorMatrix.intentLevel = 'High-Intent Lead';
        onNudgeTriggered();
        fireTrigger('high_intent_action');
      }
    }, 5000);

    // Periodic beacon flush every 15s (only if new events)
    periodicFlushInterval = setInterval(() => {
      flushBeacon();
    }, 15000);

    nudgeTimeout = setTimeout(evaluateAndTriggerNudge, 60000);

    // Final-flush listeners.
    //
    //   • `beforeunload` — reliable on desktop, flaky on iOS Safari.
    //   • `pagehide`     — fires consistently on mobile when the tab is
    //                      replaced / the user navigates away.
    //   • `visibilitychange` (→ hidden) — fires when the user backgrounds
    //                      the tab. This is the ONLY reliable "I'm about
    //                      to lose this session's data" signal on iOS
    //                      Safari. Without it, mobile sessions routinely
    //                      lost their last 15 seconds of events.
    //
    // All three call the same `sendBeacon`, which uses `navigator.sendBeacon`
    // — the only request type the browser is guaranteed to complete during
    // page tear-down.
    window.addEventListener('beforeunload', sendBeacon);
    window.addEventListener('pagehide',     sendBeacon);
    const onVisibilityHidden = () => { if (document.hidden) sendBeacon(); };
    document.addEventListener('visibilitychange', onVisibilityHidden);
    // Stash so onUnmounted can detach symmetrically.
    cleanupFns.push(() => {
      window.removeEventListener('beforeunload', sendBeacon);
      window.removeEventListener('pagehide',     sendBeacon);
      document.removeEventListener('visibilitychange', onVisibilityHidden);
    });
  });

  onUnmounted(() => {
    clearInterval(timeInterval);
    clearInterval(periodicFlushInterval);
    clearTimeout(nudgeTimeout);
    cleanupFns.forEach(fn => fn && fn());
    sendBeacon();
  });

  return {
    sessionId,
    behaviorMatrix,
    visitorMeta,
    pageVisits,
    finalizeCurrentPage,
    setNudgeCallback,
  };
}
