import { ref, reactive, onMounted, onUnmounted } from 'vue';

export function useTracker() {
    const sessionId = ref(crypto.randomUUID());
    const events = [];

    const behaviorMatrix = reactive({
        pagesViewed: [],
        timeOnSite: 0,
        hoverCount: 0,
        scrollDepth: 0,
        intentLevel: "Casual Browser"
    });

    let startTime = Date.now();
    let timeInterval = null;
    let nudgeTimeout = null;

    // Callback that the widget can override
    let onNudgeTriggered = () => { };

    const setNudgeCallback = (cb) => {
        onNudgeTriggered = cb;
    };

    const trackPageView = () => {
        behaviorMatrix.pagesViewed.push(window.location.pathname);
        logEvent("page_view", window.location.pathname);
    };

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

    const trackHovers = () => {
        const handleHover = (el) => {
            behaviorMatrix.hoverCount++;
            logEvent("hover", el.innerText || el.id || el.tagName);
        };
        document.querySelectorAll("button, a").forEach(el => {
            el.addEventListener("mouseenter", () => handleHover(el));
        });
    };

    const logEvent = (type, data) => {
        events.push({ type, data, timestamp: Date.now() });
    };

    const evaluateAndTriggerNudge = () => {
        // Stage 1 logic: Give an active nudge when timeOnSite > 30s or depth > 50%
        if (behaviorMatrix.timeOnSite >= 30 || behaviorMatrix.scrollDepth >= 50) {
            behaviorMatrix.intentLevel = "High-Intent Lead";
            onNudgeTriggered();
        }
    };

    const sendBeacon = () => {
        const host = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' ? '127.0.0.1:8000' : window.location.host;
        const url = `http://${host}/api/analytics/beacon/`;
        const payload = JSON.stringify({
            sessionId: sessionId.value,
            behaviorMatrix,
            events
        });
        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, payload);
        } else {
            fetch(url, { method: "POST", body: payload, keepalive: true }).catch(() => { });
        }
        // Clear array after sending
        events.length = 0;
    };

    let cleanupScroll = null;

    onMounted(() => {
        startTime = Date.now();
        trackPageView();
        cleanupScroll = trackScroll();

        // Give DOM a chance to render for hover listeners
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
        window.removeEventListener("beforeunload", sendBeacon);
        sendBeacon();
    });

    return {
        sessionId,
        behaviorMatrix,
        setNudgeCallback
    };
}
