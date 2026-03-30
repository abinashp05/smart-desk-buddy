const ringFill    = document.getElementById('ring-fill');
const ringEmoji   = document.getElementById('ring-emoji');
const statusText  = document.getElementById('posture-status');
const systemText  = document.getElementById('system-status');
const historyList = document.getElementById('posture-history-list');
const issuesList  = document.getElementById('issues-list');
const videoFeed   = document.getElementById('video-feed');
const statGood    = document.getElementById('stat-good');
const statBad     = document.getElementById('stat-bad');
const statSession = document.getElementById('stat-session');
const statScore   = document.getElementById('stat-score');

let lastPosture  = '';
let goodCount    = 0;
let badCount     = 0;
let sessionStart = Date.now();

function formatTime(ms) {
    const s = Math.floor(ms / 1000);
    return `${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`;
}

function updateStatus(status, system, issues) {
    ringFill.className  = 'ring-fill ' + status.toLowerCase();
    statusText.className = 'posture-status-text ' + status.toLowerCase();
    statusText.textContent = status;
    systemText.textContent = system;

    if (status === 'GOOD')      { ringEmoji.textContent = '✅'; goodCount++; }
    else if (status === 'BAD')  { ringEmoji.textContent = '⚠️'; badCount++; }
    else                        { ringEmoji.textContent = '⏳'; }

    issuesList.innerHTML = '';
    if (issues && issues.length > 0) {
        issues.forEach(issue => {
            const div = document.createElement('div');
            div.className = 'issue-item';
            div.innerHTML = `⚡ ${issue}`;
            issuesList.appendChild(div);
        });
    }

    statGood.textContent = goodCount;
    statBad.textContent  = badCount;
    const total = goodCount + badCount;
    statScore.textContent = total === 0 ? '—' : Math.round((goodCount / total) * 100);

    if (status !== lastPosture) {
        const now = new Date().toLocaleTimeString();
        const li  = document.createElement('li');
        li.className = 'history-item ' + status.toLowerCase();
        li.innerHTML = `
            <div class="h-left">
                <div class="h-dot"></div>
                <span class="h-label">${status}</span>
            </div>
            <span class="h-time">${now}</span>`;
        historyList.prepend(li);
        if (historyList.children.length > 15)
            historyList.removeChild(historyList.lastChild);
        lastPosture = status;
    }
}

function fetchStatus() {
    fetch('http://localhost:5000/status')
        .then(r => r.json())
        .then(data => updateStatus(
            data.status || 'UNKNOWN',
            data.system  || 'Monitoring Active',
            data.issues  || []
        ))
        .catch(() => updateStatus('UNKNOWN', 'Server Offline', []));
}

setInterval(fetchStatus, 1000);
setInterval(() => {
    statSession.textContent = formatTime(Date.now() - sessionStart);
}, 1000);
setInterval(() => {
    videoFeed.src = `http://localhost:5000/video_feed?t=${Date.now()}`;
}, 100);

fetchStatus();
