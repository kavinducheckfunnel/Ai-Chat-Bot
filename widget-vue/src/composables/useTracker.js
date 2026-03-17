import { reactive, onMounted, onUnmounted } from 'vue';

// Pricing / checkout URL patterns — triggers pricing hesitation FOMO
const PRICING_PATTERNS = ['/pricing', '/plans', '/checkout', '/subscribe', '/upgrade', '/buy'];

export function useTracker() {
    const sessionId = crypto.randomUUID();
    const events = [];

    const behaviorMatrix = reactive({
        pagesViewed: [],
        timeOnSite: 0,
        hoverCount: 0,
        scrollDepth: 0,
        intentLevel: "Casual Browser",
        pricingPageVisits: 0,
        exitIntentFired: false,
    });

    let startTime = Date.now();
    let timeInterval = null;
    let nudgeTimeout = null;

    // Callback that the widget can override
    let onNudgeTriggered = () => { };

    const setNudgeCallback = (cb) => {
        onNudgeTriggered = cb;
    };

    // ── API helpers ───────────────────────────────────────────────────────────
    const getApiBase = () => {
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

    // ── Page view tracking ────────────────────────────────────────────────────
    const trackPageView = () => {
        const path = window.location.pathname;
        behaviorMatrix.pagesViewed.push(path);
        logEvent("page_view", path);

        // Check if this is a pricing page
        if (PRICING_PATTERNS.some(p => path.toLowerCase().includes(p))) {
            behaviorMatrix.pricingPageVisits++;
            logEvent("pricing_visit", path);

            // Fire FOMO after 2nd visit or after 30s on the page
            if (behaviorMatrix.pricingPageVisits >= 2) {
                fireTrigger('pricing_hesitation');
            } else {
                // First visit: fire after 30 seconds of hesitation on pricing page
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
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    };

    // ── Hover tracking ────────────────────────────────────────────────────────
    const trackHovers = () => {
        const handleHover = (el) => {
            behaviorMatrix.hoverCount++;
            logEvent("hover", el.innerText || el.id || el.tagName);
        };
        document.querySelectorAll("button, a").forEach(el => {
            el.addEventListener("mouseenter", () => handleHover(el));
        });
    };

    // ── Exit-intent detection ─────────────────────────────────────────────────
    // Fires when the mouse moves above the top ~20px of the viewport (heading to browser bar / back button)
    const trackExitIntent = () => {
        const handleMouseLeave = (e) => {
            if (e.clientY > 20) return;                      // not heading out of viewport top
            if (behaviorMatrix.exitIntentFired) return;       // only fire once
            if (behaviorMatrix.timeOnSite < 5) return;        // ignore immediate bounces

            behaviorMatrix.exitIntentFired = true;
            logEvent("exit_intent", window.location.pathname);
            fireTrigger('exit_intent');
        };
        document.addEventListener("mouseleave", handleMouseLeave);
        return () => document.removeEventListener("mouseleave", handleMouseLeave);
    };

    const logEvent = (type, data) => {
        events.push({ type, data, timestamp: Date.now() });
    };

    // ── Nudge evaluation ──────────────────────────────────────────────────────
    const evaluateAndTriggerNudge = () => {
        if (behaviorMatrix.timeOnSite >= 30 || behaviorMatrix.scrollDepth >= 50) {
            behaviorMatrix.intentLevel = "High-Intent Lead";
            onNudgeTriggered();
        }
    };

    // ── Analytics beacon ──────────────────────────────────────────────────────
    const sendBeacon = () => {
        const url = `${getApiBase()}/api/analytics/beacon/`;
        const clientId = window.__CF_CLIENT_ID__;
        const payload = JSON.stringify({ sessionId, clientId, behaviorMatrix, events });
        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, payload);
        } else {
            fetch(url, { method: "POST", body: payload, keepalive: true }).catch(() => { });
        }
        events.length = 0;
    };

    let cleanupScroll = null;
    let cleanupExitIntent = null;

    onMounted(() => {
        startTime = Date.now();
        trackPageView();
        cleanupScroll = trackScroll();
        cleanupExitIntent = trackExitIntent();

        setTimeout(trackHovers, 500);

        timeInterval = setInterval(() => {
            behaviorMatrix.timeOnSite = Math.round((Date.now() - startTime) / 1000);
            evaluateAndTriggerNudge();
        }, 5000);

        nudgeTimeout = setTimeout(evaluateAndTriggerNudge, 60000);
        window.addEventListener("beforeunload", sendBeacon);
    });

    onUnmounted(() => {
        clearInterval(timeInterval);
        clearTimeout(nudgeTimeout);
        if (cleanupScroll) cleanupScroll();
        if (cleanupExitIntent) cleanupExitIntent();
        window.removeEventListener("beforeunload", sendBeacon);
        sendBeacon();
    });

    return {
        sessionId,
        behaviorMatrix,
        setNudgeCallback,
    };
}
