import sys

filepath = 'd:/Sentinel Real-time Log Anomaly Detector/web/templates/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS
css_to_add = '''
        /* Responsive */
        @media (max-width: 1024px) {
            .content-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 768px) {
            .kpi-grid { grid-template-columns: 1fr; }
            .navbar { flex-direction: column; height: auto; padding: 1rem; gap: 1rem; }
            .nav-controls { width: 100%; justify-content: space-between; }
            .controls-glass { flex-direction: column; gap: 1rem; align-items: flex-start; }
            .btn-group { width: 100%; }
            .btn { flex: 1; justify-content: center; }
        }

        /* Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            display: none; justify-content: center; align-items: center; z-index: 1000;
        }
        .modal-overlay.active { display: flex; animation: fadeIn 0.3s ease; }
        .modal-content {
            background: var(--panel-bg); border: 1px solid var(--panel-border);
            border-radius: 12px; width: 90%; max-width: 600px;
            padding: 1.5rem; max-height: 90vh; overflow-y: auto;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--panel-border); padding-bottom: 0.5rem; }
        .modal-title { font-family: var(--font-display); font-size: 1.25rem; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-muted); cursor: pointer; }
        .modal-close:hover { color: var(--text-main); }
        .modal-body pre { background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: 'Space Grotesk', monospace; font-size: 0.85rem; color: var(--text-main); border: 1px solid var(--panel-border); white-space: pre-wrap; word-break: break-all;}

        /* Toolbar */
        .table-toolbar {
            display: flex; gap: 1rem; margin-top: 1rem; flex-wrap: wrap; justify-content: space-between; width: 100%;
        }
        .toolbar-group { display: flex; gap: 0.5rem; flex-wrap: wrap; flex: 1;}
        .toolbar-input {
            background: rgba(0,0,0,0.1); border: 1px solid var(--panel-border);
            color: var(--text-main); padding: 0.5rem 1rem; border-radius: 6px;
            font-family: var(--font-main); font-size: 0.85rem; flex: 1; min-width: 150px;
        }
        [data-theme="light"] .toolbar-input { background: rgba(255,255,255,0.5); color: var(--text-main); }
        [data-theme="light"] .toolbar-input option { background: #fff; color: #000; }
        .toolbar-btn {
            background: rgba(150,150,150,0.1); border: 1px solid var(--panel-border);
            color: var(--text-main); padding: 0.5rem 1rem; border-radius: 6px;
            cursor: pointer; font-family: var(--font-main); font-size: 0.85rem;
            display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
        }
        .toolbar-btn:hover { background: rgba(150,150,150,0.2); }
        .toolbar-btn.active { background: var(--brand-gradient); color: #fff; border-color: transparent; }

        .clickable-row { cursor: pointer; }
        
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
'''
content = content.replace('    </style>', css_to_add + '\n    </style>')

# 2. Add Toolbar HTML
old_panel_header = '''                <div class="panel-header">
                    <h2 class="panel-title">Live Detection Stream</h2>
                </div>'''
new_panel_header = '''                <div class="panel-header" style="flex-direction: column; align-items: stretch; gap: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2 class="panel-title">Live Detection Stream</h2>
                    </div>
                    <div class="table-toolbar">
                        <div class="toolbar-group">
                            <input type="text" id="filter-search" class="toolbar-input" placeholder="Search IP or Payload...">
                            <select id="filter-severity" class="toolbar-input">
                                <option value="all">All Severities</option>
                                <option value="high">High (Signatures)</option>
                                <option value="medium">Medium (ML Suspicious)</option>
                            </select>
                        </div>
                        <div class="toolbar-group" style="flex: initial;">
                            <button id="btn-pause-scroll" class="toolbar-btn">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                Pause Scroll
                            </button>
                            <button id="btn-export" class="toolbar-btn">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>'''
content = content.replace(old_panel_header, new_panel_header)

# 3. Add Modal HTML
modal_html = '''
    <div class="modal-overlay" id="detail-modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Event Details</div>
                <button class="modal-close" onclick="closeModal()">
                    <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="modal-body">
                <pre id="modal-json"></pre>
            </div>
        </div>
    </div>
'''
content = content.replace('    <script>', modal_html + '\n    <script>')

# 4. Add JS Variables and Logic
js_vars = '''
        let alertsData = [];
        let isAutoScrollPaused = false;
        let searchTerm = '';
        let severityFilter = 'all';

        const filterSearch = document.getElementById('filter-search');
        const filterSeverity = document.getElementById('filter-severity');
        const btnPauseScroll = document.getElementById('btn-pause-scroll');
        const btnExport = document.getElementById('btn-export');
        const detailModal = document.getElementById('detail-modal');
        const modalJson = document.getElementById('modal-json');

        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        function playAlertSound() {
            if(audioCtx.state === 'suspended') { audioCtx.resume(); }
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
            oscillator.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.1);
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.5);
        }

        filterSearch.addEventListener('input', (e) => {
            searchTerm = e.target.value.toLowerCase();
            applyFilters();
        });

        filterSeverity.addEventListener('change', (e) => {
            severityFilter = e.target.value;
            applyFilters();
        });

        btnPauseScroll.addEventListener('click', () => {
            isAutoScrollPaused = !isAutoScrollPaused;
            if(isAutoScrollPaused) {
                btnPauseScroll.classList.add('active');
                btnPauseScroll.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg> Resume Scroll';
            } else {
                btnPauseScroll.classList.remove('active');
                btnPauseScroll.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg> Pause Scroll';
                tableBody.scrollTop = tableBody.scrollHeight;
            }
        });

        btnExport.addEventListener('click', () => {
            if(alertsData.length === 0) return;
            const headers = ['Timestamp', 'IP', 'Score', 'Reason', 'Raw Payload'];
            const csvRows = [headers.join(',')];
            alertsData.forEach(alert => {
                const row = [
                    alert.timestamp,
                    alert.ip || '',
                    alert.score,
                    `"${alert.reason}"`,
                    `"${alert.raw.replace(/"/g, '""')}"`
                ];
                csvRows.push(row.join(','));
            });
            const blob = new Blob([csvRows.join('\\n')], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('hidden', '');
            a.setAttribute('href', url);
            a.setAttribute('download', 'sentinel_alerts.csv');
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });

        function applyFilters() {
            const rows = tableBody.querySelectorAll('tr:not(#empty-state-row)');
            rows.forEach((row, index) => {
                const alert = alertsData[index];
                if(!alert) return;
                
                let matchSearch = true;
                if(searchTerm) {
                    matchSearch = (alert.ip && alert.ip.toLowerCase().includes(searchTerm)) || 
                                  alert.raw.toLowerCase().includes(searchTerm);
                }
                
                let matchSeverity = true;
                if(severityFilter !== 'all') {
                    const isSig = alert.reason.includes("Signature");
                    if(severityFilter === 'high' && !isSig) matchSeverity = false;
                    if(severityFilter === 'medium' && isSig) matchSeverity = false;
                }
                
                row.style.display = (matchSearch && matchSeverity) ? '' : 'none';
            });
        }

        function openModal(index) {
            const alert = alertsData[index];
            if(!alert) return;
            modalJson.textContent = JSON.stringify(alert, null, 2);
            detailModal.classList.add('active');
        }
        function closeModal() {
            detailModal.classList.remove('active');
        }
'''
content = content.replace('        let totalCount = 0;', js_vars + '\n        let totalCount = 0;')

# 5. Modify startServer to clear alertsData
old_start = '''                if (emptyStateRow) {
                    emptyStateRow.innerHTML = '<td colspan="5" style="background:transparent; border:none;"><div class="empty-state">Engine initialized. Listening for security events...</div></td>';
                }
                isFirstAlert = true;
                setTimeout(updateStatus, 1500);'''
new_start = '''                alertsData = [];
                tableBody.innerHTML = '<tr id="empty-state-row"><td colspan="5" style="background:transparent; border:none;"><div class="empty-state">Engine initialized. Listening for security events...</div></td></tr>';
                emptyStateRow = document.getElementById('empty-state-row');
                isFirstAlert = true;
                
                totalCount = 0; highSeverityCount = 0; mlCount = 0;
                kpiTotal.textContent = 0; kpiHigh.textContent = 0; kpiMl.textContent = 0;
                
                if (anomalyChart) {
                    anomalyChart.data.labels = [];
                    anomalyChart.data.datasets[0].data = [];
                    anomalyChart.update();
                }
                
                setTimeout(updateStatus, 1500);'''
content = content.replace(old_start, new_start)

# 6. Modify eventSource.onmessage
old_msg = '''                // Determine severity badge
                const isSignature = alert.reason.includes("Signature");'''
new_msg = '''                // Determine severity badge
                alertsData.push(alert);
                const alertIndex = alertsData.length - 1;
                const isSignature = alert.reason.includes("Signature");
                if (isSignature) {
                    playAlertSound();
                }'''
content = content.replace(old_msg, new_msg)

old_tr_create = '''                const tr = document.createElement('tr');'''
new_tr_create = '''                const tr = document.createElement('tr');
                tr.className = 'clickable-row';
                tr.onclick = () => openModal(alertIndex);'''
content = content.replace(old_tr_create, new_tr_create)

old_scroll = '''                tableBody.appendChild(tr);
                tableBody.scrollTop = tableBody.scrollHeight; // Auto-scroll'''
new_scroll = '''                
                let matchSearch = true;
                if(searchTerm) {
                    matchSearch = (alert.ip && alert.ip.toLowerCase().includes(searchTerm)) || 
                                  alert.raw.toLowerCase().includes(searchTerm);
                }
                let matchSeverity = true;
                if(severityFilter !== 'all') {
                    if(severityFilter === 'high' && !isSignature) matchSeverity = false;
                    if(severityFilter === 'medium' && isSignature) matchSeverity = false;
                }
                tr.style.display = (matchSearch && matchSeverity) ? '' : 'none';

                tableBody.appendChild(tr);
                if(!isAutoScrollPaused) {
                    tableBody.scrollTop = tableBody.scrollHeight; // Auto-scroll
                }'''
content = content.replace(old_scroll, new_scroll)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')
