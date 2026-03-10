(function() {
    window.CheckfunnelTracker = {
        sessionId: crypto.randomUUID(),
        events: [],
        behaviorMatrix: {
            pagesViewed: [],
            timeOnSite: 0,
            hoverCount: 0,
            scrollDepth: 0,
            intentLevel: "Casual Browser"
        },
        startTime: Date.now(),
        
        init: function() {
            this.trackPageView();
            this.trackScroll();
            this.trackHovers();
            
            // Send beacon periodically or before unload
            window.addEventListener("beforeunload", () => this.sendBeacon());
            setInterval(() => this.updateTimeOnSite(), 5000);
            
            // 1 minute evaluation (Trigger)
            setTimeout(() => this.evaluateAndTriggerNudge(), 60000);
        },
        
        trackPageView: function() {
            this.behaviorMatrix.pagesViewed.push(window.location.pathname);
            this.logEvent("page_view", window.location.pathname);
        },
        
        trackScroll: function() {
            window.addEventListener("scroll", () => {
                let docHeight = Math.max(
                    document.body.scrollHeight, document.documentElement.scrollHeight,
                    document.body.offsetHeight, document.documentElement.offsetHeight,
                    document.body.clientHeight, document.documentElement.clientHeight
                );
                let depth = (window.scrollY / (docHeight - window.innerHeight)) * 100;
                if (depth > this.behaviorMatrix.scrollDepth) {
                    this.behaviorMatrix.scrollDepth = Math.round(depth);
                }
            });
        },
        
        trackHovers: function() {
            document.querySelectorAll("button, a").forEach(el => {
                el.addEventListener("mouseenter", () => {
                    this.behaviorMatrix.hoverCount++;
                    this.logEvent("hover", el.innerText || el.id);
                });
            });
        },
        
        updateTimeOnSite: function() {
            this.behaviorMatrix.timeOnSite = Math.round((Date.now() - this.startTime) / 1000);
        },
        
        evaluateAndTriggerNudge: function() {
            if (this.behaviorMatrix.timeOnSite >= 30 || this.behaviorMatrix.scrollDepth >= 50) {
                this.behaviorMatrix.intentLevel = "High-Intent Lead";
                if (window.CheckfunnelWidget) {
                    window.CheckfunnelWidget.triggerNudge();
                }
            }
        },
        
        logEvent: function(type, data) {
            this.events.push({ type: type, data: data, timestamp: Date.now() });
        },
        
        sendBeacon: function() {
            // Ideally endpoint depends on actual host. Hardcoded to 127.0.0.1 for local dev.
            const url = "http://127.0.0.1:8000/api/analytics/beacon/";
            const payload = JSON.stringify({
                sessionId: this.sessionId,
                behaviorMatrix: this.behaviorMatrix,
                events: this.events
            });
            if (navigator.sendBeacon) {
                navigator.sendBeacon(url, payload);
            } else {
                fetch(url, { method: "POST", body: payload, keepalive: true }).catch(() => {});
            }
            this.events = [];
        }
    };
    
    // Initialize Tracker
    if(document.readyState === 'complete' || document.readyState === 'interactive') {
        window.CheckfunnelTracker.init();
    } else {
        document.addEventListener('DOMContentLoaded', () => window.CheckfunnelTracker.init());
    }
})();
