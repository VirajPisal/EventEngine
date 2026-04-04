
        /* ===== AUTH CHECK & INIT ===== */
        (function () {
            if (!getToken() || getRole() !== 'organizer') {
                window.location.href = '/frontend/login.html';
                return;
            }
            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
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
            return String(t).replace(/[&<>\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
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
                const d = await r.json();
                if (d.success) {
                    allEvents = d.events;
                    document.getElementById('eventCount').textContent = d.count;
                    renderNavigator();
                }
            } catch (e) { 
                console.error('loadEvents', e); 
                showToast('API unreachable. Is the server running on port 8000?', 'error');
            }
        }

        function renderNavigator() {
            const el = document.getElementById('eventList');
            const showCan = document.getElementById('showCancelled').checked;
            const filtered = allEvents.filter(ev => showCan || ev.state !== 'CANCELLED');
            
            if (!filtered.length) {
                el.innerHTML = '<div class="empty">No events found.</div>';
                return;
            }

            el.innerHTML = filtered.map(ev => `
                <div class="event-card ${ev.id === selectedEventId ? 'selected' : ''}" onclick="selectEvent(${ev.id})">
                    <div class="event-card-top">
                        <span class="event-card-name">${esc(ev.name)}</span>
                        <span class="event-card-state state-${ev.state}">${ev.state.replace(/_/g, ' ')}</span>
                    </div>
                    <div class="event-card-meta">
                        <span>📅 ${fmtDate(ev.start_time)}</span>
                        <span>👥 ${ev.stats?.total_registered || 0} Reg.</span>
                    </div>
                </div>
            `).join('');
        }

        function selectEvent(id) {
            selectedEventId = id;
            renderNavigator();
            loadWorkspace(id);
        }

        /* ===== WORKSPACE (Panel 2) ===== */
        async function loadWorkspace(id) {
            const ev = allEvents.find(e => e.id === id);
            if (!ev) return;

            // Display components
            document.getElementById('workspaceEmptyState').style.display = 'none';
            document.getElementById('eventDetailView').style.display = 'block';
            document.getElementById('aiSection').style.display = 'block';

            // Set basic info
            document.getElementById('viewEventName').textContent = ev.name;
            document.getElementById('viewEventMeta').textContent = `${fmtDate(ev.start_time)} @ ${ev.venue || ev.event_type}`;
            document.getElementById('activeEventStatus').innerHTML = `<span class="event-card-state state-${ev.state}">${ev.state.replace(/_/g, ' ')}</span>`;

            // Set metrics
            const s = ev.stats || {};
            document.getElementById('statRegistered').textContent = s.total_registered || 0;
            document.getElementById('statConfirmed').textContent = s.total_confirmed || 0;
            document.getElementById('statAttended').textContent = s.total_attended || 0;
            document.getElementById('statCapacity').textContent = ev.max_participants || '∞';

            // Update charts
            renderCharts(s, ev);

            // Populate Action Center
            const actionCenter = document.getElementById('eventActionCenter');
            actionCenter.innerHTML = '';
            
            if (ev.state === 'CREATED') {
                actionCenter.innerHTML = `
                    <div class="ai-draft-section" style="border: 1px dashed var(--db-accent); background: rgba(99,102,241,0.05); text-align: center;">
                        <p style="color: var(--db-accent); font-weight: 600; margin-bottom: 5px;">🚀 Event is currently a Private Draft</p>
                        <p style="font-size: 0.75rem; color: var(--db-text-dim); margin-bottom: 12px;">Participants cannot see or register for this event until you launch it.</p>
                        <button class="btn-create-event" style="width: auto; padding: 10px 25px;" 
                            onclick="transitionEvent(${ev.id}, 'REGISTRATION_OPEN')">🚀 Launch Public Registration</button>
                    </div>
                `;
            } else if (ev.state === 'REGISTRATION_OPEN') {
                actionCenter.innerHTML = `
                    <div class="ai-draft-section" style="border: 1px dashed var(--db-green); background: rgba(34,197,94,0.05); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <p style="color: var(--db-green); font-weight: 600; margin: 0;">✅ Registration is LIVE</p>
                            <p style="font-size: 0.75rem; color: var(--db-text-dim); margin: 4px 0 0;">The event is visible to all participants for signup.</p>
                        </div>
                        <button class="btn-action" onclick="promoteEvent(${ev.id})" style="background: var(--db-accent); color: white; border: none; padding: 8px 15px;">📣 Force Pro-active Promotion</button>
                    </div>
                `;
            }

            // Fetch AI Insights
            fetchAIInsights(id);
            // Fetch Participants
            loadParticipants(id);
        }

        async function transitionEvent(id, newState) {
            try {
                const r = await fetch(API + `/api/events/${id}/transition`, {
                    method: 'POST',
                    headers: hdrs(),
                    body: JSON.stringify({ new_state: newState, reason: 'Manual trigger from dashboard' })
                });
                const d = await r.json();
            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
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
            return String(t).replace(/[&<>\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
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
                const d = await r.json();
                if (d.success) {
                    showToast(`Event transitioned to ${newState}`);
                    loadEvents(); // Refresh all
                } else {
                    showToast(d.message || 'Transition failed', 'error');
                }
            } catch (e) { showToast('Connection error', 'error'); }
        }

        async function promoteEvent(id) {
            try {
                showToast('AI Agent is sending promotional invites...', 'info');
                const r = await fetch(API + `/api/events/${id}/promote`, { method: 'POST', headers: hdrs() });
                const d = await r.json();
                if (d.success) showToast(`Promoted to ${d.emails_sent} potential participants!`);
            } catch (e) { showToast('Promotion failed', 'error'); }
        }

        function renderCharts(stats, event) {
            const ctxReg = document.getElementById('registrationChart').getContext('2d');
            if (regChart) regChart.destroy();
            
            // Dummy trend for presentation
            const baseline = Math.floor(stats.total_registered * 0.4);
            const mid = Math.floor(stats.total_registered * 0.7);

            regChart = new Chart(ctxReg, {
                type: 'line',
                data: {
                    labels: ['7d', '6d', '5d', '4d', '3d', '2d', '1d', 'Now'],
                    datasets: [{
                        label: 'Registrations',
                        data: [0, 0, baseline, baseline, mid, mid, stats.total_registered, stats.total_registered],
                        borderColor: '#6366f1',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        pointRadius: 0
                    }]
                },
                options: { 
                    maintainAspectRatio: false, 
                    plugins: { legend: { display: false } }, 
                    scales: { 
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8b8fa3', font: { size: 10 } } },
                        x: { grid: { display: false }, ticks: { color: '#8b8fa3', font: { size: 10 } } } 
                    } 
                }
            });

            const ctxAtt = document.getElementById('attendanceChart').getContext('2d');
            if (attChart) attChart.destroy();
            attChart = new Chart(ctxAtt, {
                type: 'doughnut',
                data: {
                    labels: ['Attended', 'Missed'],
                    datasets: [{
                        data: [stats.total_attended || 0, Math.max(0, (stats.total_confirmed || 0) - (stats.total_attended || 0))],
                        backgroundColor: ['#22c55e', 'rgba(239, 68, 68, 0.2)'],
                        borderColor: ['#22c55e', '#ef4444'],
                        borderWidth: 1
                    }]
                },
                options: { 
                    maintainAspectRatio: false, 
                    cutout: '75%', 
                    plugins: { 
                        legend: { position: 'bottom', labels: { color: '#8b8fa3', boxWidth: 8, font: { size: 10 } } } 
                    } 
                }
            });
        }

        /* ===== AI ASSISTANT (Panel 3) ===== */
        async function fetchAIInsights(id) {
            const loading = document.getElementById('aiLoading');
            const content = document.getElementById('aiContent');
            
            loading.style.display = 'block';
            content.style.display = 'none';

            try {
                const r = await fetch(API + `/api/agent/insights/${id}`, { headers: hdrs() });
                const d = await r.json();
                
                loading.style.display = 'none';
                content.style.display = 'block';

            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
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
            return String(t).replace(/[&<>\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
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
                const d = await r.json();
                if (d.success) {
                    document.getElementById('aiStrategyText').textContent = d.strategy;
                    const list = document.getElementById('aiActionList');
                    list.innerHTML = d.actions.map(act => `
                        <div class="ai-action-item">
                            <span class="icon">➜</span>
                            <span>${act}</span>
                        </div>
                    `).join('');
                }
            } catch (e) { 
                loading.style.display = 'none';
                console.error('AI Insights Error', e); 
            }
        }

        /* ===== PARTICIPANTS ===== */
        async function loadParticipants(id = selectedEventId) {
            const container = document.getElementById('participantTableContainer');
            container.innerHTML = '<div class="empty">Loading...</div>';
            try {
                const r = await fetch(API + `/api/events/${id}/participants`, { headers: hdrs() });
                const d = await r.json();
                if (d.success && d.participants && d.participants.length) {
                    container.innerHTML = `
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-top: 10px;">
                            <thead>
                                <tr style="text-align: left; color: var(--db-text-dim); border-bottom: 1px solid var(--db-border);">
                                    <th style="padding: 10px;">Name</th>
                                    <th style="padding: 10px;">Status</th>
                                    <th style="padding: 10px;">Joined</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${d.participants.map(reg => `
                                    <tr style="border-bottom: 1px solid rgba(45, 49, 65, 0.5);">
                                        <td style="padding: 10px;">${esc(reg.name)}</td>
                                        <td style="padding: 10px;"><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--db-text-dim);">${reg.status}</span></td>
                                        <td style="padding: 10px;">${fmtDate(reg.registered_at)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                } else {
                    container.innerHTML = '<div class="empty">No participants registered yet.</div>';
                }
            } catch (e) { container.innerHTML = '<div class="empty">Error loading participants.</div>'; }
        }

        /* ===== AGENT INBOX (Panel 3 - Bottom) ===== */
        async function loadPendingActions() {
            try {
                const r = await fetch(API + '/api/agent/pending-actions', { headers: hdrs() });
                const d = await r.json();
                document.getElementById('pendingCount').textContent = d.count || 0;
                const el = document.getElementById('agentInbox');
                if (!d.count) {
                    el.innerHTML = '<div class="empty" style="padding: 10px 0;">Agent is monitoring lifecycle...</div>';
                    return;
                }
                el.innerHTML = d.actions.map(a => `
                    <div class="action-card" style="padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <div class="action-card-header">
                            <span class="action-type" style="font-size:0.8rem;">${a.action_type.replace(/_/g, ' ')}</span>
                            <button class="btn-action" style="padding: 2px 8px;" onclick="approveAction(${a.id})">Approve</button>
                        </div>
                        <div class="action-desc" style="margin-top: 5px; font-size: 0.75rem;">${esc(a.description)}</div>
                    </div>
                `).join('');
            } catch (e) { console.error('loadPending', e); }
        }

        async function approveAction(id) {
            try {
                const r = await fetch(API + `/api/agent/actions/${id}/approve`, { method: 'POST', headers: hdrs() });
                const d = await r.json();
                showToast(d.success ? 'Action executed' : 'Failed', d.success ? 'success' : 'error');
                loadPendingActions();
            } catch (e) { console.error(e); }
        }

        /* ===== NLP EVENT CREATION ===== */
        async function parseNLP() {
            const text = document.getElementById('nlpInput').value.trim();
            if (!text) return;
            const btn = document.querySelector('.btn-parse');
            btn.disabled = true; btn.textContent = 'Analyzing...';
            try {
                const r = await fetch(API + '/api/events/parse-natural-language', {
                    method: 'POST', headers: hdrs(), body: JSON.stringify({ text })
                });
                const d = await r.json();
            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
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
            return String(t).replace(/[&<>\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
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
                const d = await r.json();
                if (d.success) {
                    showParsedPreview(d.parsed);
                } else { showToast('Parse failed', 'error'); }
            } catch (e) { console.error(e); }
            btn.disabled = false; btn.textContent = '🚀 Build with AI';
        }

        function showParsedPreview(p) {
            const preview = document.getElementById('parsedPreview');
            const fields = document.getElementById('parsedFields');
            preview.style.display = 'block';
            
            // Auto-generate meet link if online and not provided
            let link = p.meeting_link || '';
            if (!link && p.event_type === 'ONLINE') {
                const id = Math.random().toString(36).substring(2, 5) + '-' + 
                           Math.random().toString(36).substring(2, 6) + '-' + 
                           Math.random().toString(36).substring(2, 5);
                link = `https://meet.google.com/${id}`;
            }

            fields.innerHTML = `
                <div class="ai-draft-section">
                    <label class="section-label">📍 Core Details</label>
                    <div class="parsed-field">
                        <label>Event Title</label>
                        <input type="text" id="p_name" value="${p.name || ''}" placeholder="Enter event name...">
                    </div>
                    <div class="parsed-field">
                        <label>Start Date/Time</label>
                        <input type="datetime-local" id="p_start" value="${toLocalInput(p.start_time)}">
                    </div>
                    <div class="parsed-field">
                        <label>End Date/Time</label>
                        <input type="datetime-local" id="p_end" value="${toLocalInput(p.end_time || new Date(new Date(p.start_time).getTime() + 7200000).toISOString())}">
                    </div>
                </div>

                <div class="ai-draft-section">
                    <label class="section-label">🎪 Type & Logistics</label>
                    <div class="parsed-field">
                        <label>Event Format</label>
                        <select id="p_type" style="width: 100%; padding: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--db-border); border-radius: 4px; color: white;">
                            <option value="ONLINE" ${p.event_type === 'ONLINE' ? 'selected' : ''}>Online</option>
                            <option value="OFFLINE" ${p.event_type === 'OFFLINE' ? 'selected' : ''}>Offline</option>
                            <option value="HYBRID" ${p.event_type === 'HYBRID' ? 'selected' : ''}>Hybrid</option>
                        </select>
                    </div>
                    <div class="parsed-field">
                        <label>Max Seats (Capacity)</label>
                        <input type="number" id="p_cap" value="${p.max_participants || 100}">
                    </div>
                    <div class="parsed-field" id="p_venue_group">
                        <label>Location / Venue</label>
                        <input type="text" id="p_venue" value="${p.venue || ''}" placeholder="Physical address or TBD">
                    </div>
                    <div class="parsed-field" id="p_link_group" style="display: ${p.event_type === 'OFFLINE' ? 'none' : 'block'};">
                        <label>Meeting Link</label>
                        <input type="text" id="p_link" value="${link}" placeholder="https://meet.google.com/...">
                    </div>
                </div>

                <div class="ai-draft-section">
                    <label class="section-label">✉️ Custom Communication</label>
                    <div class="parsed-field">
                        <label>Custom Message (Invitations & Confirmations)</label>
                        <textarea id="p_custom_email" style="min-height: 100px; font-size: 0.8rem; padding: 10px;" 
                            placeholder="Add a custom welcome message for the confirmation email...">${p.custom_email_template || `Dear Participant, Greetings! Thank you for registering for the **${p.name || 'Event'}**.`}</textarea>
                    </div>
                    <div class="parsed-field">
                        <label>Certificate Template (URL or ID)</label>
                        <input type="text" id="p_cert" value="${p.certificate_template || ''}" placeholder="Leave blank for no certificates">
                    </div>
                </div>
            `;

            // Toggle link visibility based on type
            const typeSel = document.getElementById('p_type');
            const linkGrp = document.getElementById('p_link_group');
            typeSel.addEventListener('change', () => {
                linkGrp.style.display = (typeSel.value === 'OFFLINE') ? 'none' : 'block';
                if (typeSel.value === 'ONLINE' && !document.getElementById('p_link').value) {
                    const id = Math.random().toString(36).substring(2, 5) + '-' + 
                               Math.random().toString(36).substring(2, 6) + '-' + 
                               Math.random().toString(36).substring(2, 5);
                    document.getElementById('p_link').value = `https://meet.google.com/${id}`;
                }
            });
        }

        async function createEventFromParsed() {
            const data = {
                name: document.getElementById('p_name').value,
                description: 'Created via AI Assistant',
                start_time: new Date(document.getElementById('p_start').value).toISOString(),
                end_time: document.getElementById('p_end').value ? new Date(document.getElementById('p_end').value).toISOString() : null,
                event_type: document.getElementById('p_type').value,
                venue: document.getElementById('p_venue').value,
                meeting_link: document.getElementById('p_link').value,
                max_participants: parseInt(document.getElementById('p_cap').value) || 100,
                custom_email_template: document.getElementById('p_custom_email').value,
                certificate_template: document.getElementById('p_cert').value || null
            };
            try {
                const r = await fetch(API + '/api/events/', { method: 'POST', headers: hdrs(), body: JSON.stringify(data) });
                const d = await r.json();
            document.getElementById('userName').textContent = getName() || getEmail() || 'Organizer';
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
            return String(t).replace(/[&<>\"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
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
                const d = await r.json();
                if (d.success) {
                    showToast('Event created successfully!');
                    document.getElementById('parsedPreview').style.display = 'none';
                    document.getElementById('nlpInput').value = '';
                    loadEvents();
                }
            } catch (e) { console.error(e); }
        }

        /* ===== UTILS ===== */
        function esc(t) { if (!t) return ''; const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
        function fmtDate(ds) { 
            if (!ds) return '-'; 
            const d = new Date(ds);
            return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
        }
        function toLocalInput(ds) {
            if (!ds) return '';
            const d = new Date(ds);
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            return d.toISOString().slice(0, 16);
        }
        function showToast(msg, type = 'success') {
            const t = document.getElementById('toast');
            t.textContent = msg; t.className = 'toast ' + type + ' show';
            setTimeout(() => t.classList.remove('show'), 3000);
        }

        /* INIT */
        document.addEventListener('DOMContentLoaded', () => {
             init().catch(e => {
                 console.error('Init failed:', e);
                 showToast('Dashboard failed to initialize: ' + e.message, 'error');
             });
        });
    