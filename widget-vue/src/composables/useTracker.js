import { reactive, ref, onMounted, onUnmounted } from 'vue';

// Pricing / checkout URL patterns — triggers pricing hesitation FOMO
const PRICING_PATTERNS = ['/pricing', '/plans', '/checkout', '/subscribe', '/upgrade', '/buy'];

// ── User-agent parsing helpers ────────────────────────────────────────────────
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

// ── First-visit detection ─────────────────────────────────────────────────────
const RETURNING_KEY = '__cf_returning__';
function checkReturning() {
    const isReturning = !!localStorage.getItem(RETURNING_KEY);
    localStorage.setItem(RETURNING_KEY, '1');
    return isReturning;
}

export function useTracker() {
    const SESSION_KEY = '__cf_sid__';
    const sessionId = sessionStorage.getItem(SESSION_KEY) || (() => {
        const id = crypto.randomUUID();
        sessionStorage.setItem(SESSION_KEY, id);
        return id;
    })();

    const events = [];

    const behaviorMatrix = reactive({
        pagesViewed: [],
        timeOnSite: 0,
        hoverCount: 0,
        scrollDepth: 0,
        intentLevel: 'Casual Browser',
        pricingPageVisits: 0,
        exitIntentFired: false,
    });

    // Visitor metadata (populated asynchronously)
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

    // Detailed page visit log with durations
    const pageVisits = ref([]);
    let currentPageEntry = null;

    let startTime = Date.now();
    let timeInterval = null;
    let nudgeTimeout = null;
    let onNudgeTriggered = () => { };

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
        }).catch(() => { });
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
        } catch { /* geo is best-effort */ }
    };

    // ── Page view tracking ────────────────────────────────────────────────────
    const finalizeCurrentPage = () => {
        if (!currentPageEntry) return;
        const duration = Math.round((Date.now() - currentPageEntry.enteredAt) / 1000);
        pageVisits.value.push({
            url: currentPageEntry.url,
            title: currentPageEntry.title,
            duration_seconds: duration,
            visited_at: new Date(currentPageEntry.enteredAt).toISOString(),
        });
        currentPageEntry = null;
    };

    const trackPageView = () => {
        finalizeCurrentPage();
        const path = window.location.pathname;
        currentPageEntry = {
            url: path,
            title: document.title || path,
            enteredAt: Date.now(),
        };
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
    };

    // ── Scroll tracking ───────────────────────────────────────────────────────
    const trackScroll = () => {
        const handleScroll = () => {
            let docHeight = Math.max(
                document.body.scrollHeight, document.documentElement.scrollHeight,
                document.body.offsetHeight, document.documentElement.offsetHeight,
                document.body.clientHeight, document.documentElement.clientHeight
            );
            let depth = (window.scrollY / (docHeight - window.innerHeight)) * 100;
            if (depth > behaviorMatrix.scrollDepth) {
                behaviorMatrix.scrollDepth = Math.round(depth);
            }
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    };

    // ── Hover tracking ────────────────────────────────────────────────────────
    const trackHovers = () => {
        const handleHover = (el) => {
            behaviorMatrix.hoverCount++;
            logEvent('hover', el.innerText || el.id || el.tagName);
        };
        document.querySelectorAll('button, a').forEach(el => {
            el.addEventListener('mouseenter', () => handleHover(el));
        });
    };

    // ── Exit-intent detection ─────────────────────────────────────────────────
    const trackExitIntent = () => {
        const handleMouseLeave = (e) => {
            if (e.clientY > 20) return;
            if (behaviorMatrix.exitIntentFired) return;
            if (behaviorMatrix.timeOnSite < 5) return;
            behaviorMatrix.exitIntentFired = true;
            logEvent('exit_intent', window.location.pathname);
            fireTrigger('exit_intent');
        };
        document.addEventListener('mouseleave', handleMouseLeave);
        return () => document.removeEventListener('mouseleave', handleMouseLeave);
    };

    const logEvent = (type, data) => {
        events.push({ type, data, timestamp: Date.now() });
    };

    // ── Nudge evaluation ──────────────────────────────────────────────────────
    const evaluateAndTriggerNudge = () => {
        if (behaviorMatrix.timeOnSite >= 30 || behaviorMatrix.scrollDepth >= 50) {
            behaviorMatrix.intentLevel = 'High-Intent Lead';
            onNudgeTriggered();
        }
    };

    // ── Analytics beacon ──────────────────────────────────────────────────────
    const sendBeacon = () => {
        finalizeCurrentPage();
        const url = `${getApiBase()}/api/analytics/beacon/`;
        const clientId = window.__CF_CLIENT_ID__;
        const payload = JSON.stringify({ sessionId, clientId, behaviorMatrix, events });
        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, payload);
        } else {
            fetch(url, { method: 'POST', body: payload, keepalive: true }).catch(() => { });
        }
        events.length = 0;
    };

    let cleanupScroll = null;
    let cleanupExitIntent = null;

    onMounted(() => {
        startTime = Date.now();
        trackPageView();
        fetchGeo();
        cleanupScroll = trackScroll();
        cleanupExitIntent = trackExitIntent();

        setTimeout(trackHovers, 500);

        timeInterval = setInterval(() => {
            behaviorMatrix.timeOnSite = Math.round((Date.now() - startTime) / 1000);
            evaluateAndTriggerNudge();
        }, 5000);

        nudgeTimeout = setTimeout(evaluateAndTriggerNudge, 60000);
        window.addEventListener('beforeunload', sendBeacon);
    });

    onUnmounted(() => {
        clearInterval(timeInterval);
        clearTimeout(nudgeTimeout);
        if (cleanupScroll) cleanupScroll();
        if (cleanupExitIntent) cleanupExitIntent();
        window.removeEventListener('beforeunload', sendBeacon);
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
