import re

with open('frontend/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
        })();

        async function init() {
            await loadEvents();
            await loadPendingActions();
            setInterval(() => {
                loadEvents();
                loadPendingActions();
            }, 30000);
        }

        function doLogout() { logout(); window.location.href = '/frontend/login.html'; }

        const API = (window.location.protocol === 'file:') ? 'http://localhost:8000' : '';
        const hdrs = () => ({ ...authHeaders(), 'Content-Type': 'application/json' });

        /* ===== HELPERS ===== */
        function toLocalInput(iso) {
            if (!iso) return '';
            const d = new Date(iso);
            if (isNaN(d.getTime())) return '';
            const offset = d.getTimezoneOffset() * 60000;
            return new Date(d.getTime() - offset).toISOString().slice(0, 16);
        }

        function fmtDate(iso) {
            if (!iso) return 'TBD';
            const d = new Date(iso);
            return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        }

        function fmtDateTime(iso) {
            return fmtDate(iso);
        }

        function esc(t) {
            if (!t) return '';
            return String(t).replace(/[&<>\\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\\"':'&quot;',"'":'&#39;'}[m]));
        }

        /* ===== STATE ===== */
        let allEvents = [];
        let selectedEventId = null;
        let regChart = null;
        let attChart = null;

        /* ===== NAVIGATOR (Panel 1) ===== */
        async function loadEvents() {
            try {
                const r = await fetch(API + '/api/events/?limit=100');
                const d = await r.json();'''

content = content.replace('                if (d.success) {', replacement + '\n                if (d.success) {')

with open('frontend/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully!')
