export function recordVisit() {
    try {
        const keyName = "kundali_visitor_key";
        let visitorKey = localStorage.getItem(keyName);
        if (!visitorKey) {
            visitorKey = `visitor_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
            localStorage.setItem(keyName, visitorKey);
        }
        fetch("/api/analytics/visit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                visitor_key: visitorKey,
                path: window.location.pathname || "/",
                referrer: document.referrer || "",
            }),
            keepalive: true,
        }).catch(() => {});
    } catch (_err) {
        // Analytics should never interrupt user workflows.
    }
}
