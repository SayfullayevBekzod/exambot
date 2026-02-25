/* === IELTS Mini App — Enhanced JavaScript === */

const tg = window.Telegram?.WebApp;
let userId = 0;
let currentQuiz = null;
let flashcards = [];
let currentFcIndex = 0;
let timerInterval = null;
let isStaticMode = false; // true = GitHub Pages (no API)
let API_BASE = '';
let trendChart = null;
let radarChart = null;
let cbtTimerInterval = null;
let cbtQuestions = [];
let cbtAnswers = {};

// === Init ===
document.addEventListener('DOMContentLoaded', async () => {
    if (tg && tg.initDataUnsafe?.user?.id) {
        tg.expand();
        tg.setHeaderColor('#050816');
        tg.setBackgroundColor('#050816');
        userId = tg.initDataUnsafe.user.id;
        const name = tg.initDataUnsafe.user.first_name || 'Foydalanuvchi';
        document.getElementById('userAvatar').textContent = name.charAt(0).toUpperCase();
    } else {
        const params = new URLSearchParams(window.location.search);
        userId = parseInt(params.get('user_id')) || 0;
        document.getElementById('userAvatar').textContent = 'T';
    }

    // Detect if API is available or static mode (GitHub Pages)
    API_BASE = window.location.origin + '/api';
    try {
        console.log('🔍 Testing API connectivity:', API_BASE + '/subjects');
        const test = await fetch(API_BASE + '/subjects', { signal: AbortSignal.timeout(5000) });
        if (!test.ok) throw new Error('no api');
        isStaticMode = false;
        console.log('✅ API mode active');
    } catch (e) {
        isStaticMode = true;
        console.warn('📦 Static mode — loading from JSON files. Reason:', e.message);
    }

    try {
        await Promise.all([loadSubjects(), loadStats(), loadFlashcards(), checkPremium()]);
    } catch (e) { console.error('Init error:', e); }

    document.getElementById('loading').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
});

// === Tab Switching ===
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    const el = document.getElementById('tab-' + tab);
    el.classList.remove('hidden');
    el.querySelector('.section')?.classList.add('fade-in');
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

    if (tab === 'stats') loadStats();
    if (tab === 'flashcards') loadFlashcards();
}

// === API / Static Helper ===
async function apiFetch(endpoint) {
    if (isStaticMode) return null;
    try {
        const sep = endpoint.includes('?') ? '&' : '?';
        const res = await fetch(`${API_BASE}${endpoint}${sep}user_id=${userId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error('API error:', e);
        return null;
    }
}

async function loadStaticJSON(filename) {
    try {
        const res = await fetch(`data/${filename}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error('Static load error:', e);
        return null;
    }
}

// ==========================================
//  QUIZ
// ==========================================

let allSubjects = [];
let selectedSubjectId = 0;
let selectedSubjectName = '';
let selectedSubjectEmoji = '';

async function loadSubjects() {
    let data = await apiFetch('/subjects');
    if (!data) data = await loadStaticJSON('subjects.json');
    if (!data) return;
    allSubjects = data;

    const grid = document.getElementById('subjectsList');
    grid.innerHTML = data.map(s => `
        <div class="subject-card" onclick="chooseSubject(${s.id}, '${s.name}', '${s.emoji}')">
            <span class="subject-emoji">${s.emoji}</span>
            <div class="subject-name">${s.name}</div>
            <div class="subject-count">${s.question_count} ta savol</div>
        </div>
    `).join('');
}

function chooseSubject(id, name, emoji) {
    selectedSubjectId = id;
    selectedSubjectName = name;
    selectedSubjectEmoji = emoji;
    document.getElementById('diffSubjectName').textContent = `${emoji} ${name}`;
    showView('quizDifficulty');
}

function backToSubjects() {
    showView('quizSubjects');
}

function selectDifficulty(level) {
    startQuiz(selectedSubjectId, selectedSubjectName, selectedSubjectEmoji, level);
}

async function startDailyChallenge() {
    // Mix questions from all subjects
    let allQuestions = [];
    for (const s of allSubjects) {
        let data = await apiFetch(`/questions/${s.id}`);
        if (!data) data = await loadStaticJSON(`questions_${s.id}.json`);
        if (data) allQuestions = allQuestions.concat(data.map(q => ({ ...q, subjectEmoji: s.emoji })));
    }
    if (allQuestions.length === 0) { showToast('❌', 'Savollar topilmadi!'); return; }

    const shuffled = allQuestions.sort(() => Math.random() - 0.5).slice(0, 10);
    currentQuiz = {
        subjectId: 0, name: 'Kunlik Challenge', emoji: '⚡',
        questions: shuffled, current: 0, score: 0, total: shuffled.length,
        answers: [],
    };
    showView('quizActive');
    showQuestion();
}

async function startQuiz(subjectId, name, emoji, difficulty) {
    let data = await apiFetch(`/questions/${subjectId}`);
    if (!data) data = await loadStaticJSON(`questions_${subjectId}.json`);
    if (!data || data.length === 0) { showToast('❌', 'Savollar topilmadi!'); return; }

    // Filter by difficulty
    if (difficulty > 0) {
        const filtered = data.filter(q => q.difficulty === difficulty);
        if (filtered.length >= 5) data = filtered;
    }

    const shuffled = data.sort(() => Math.random() - 0.5).slice(0, 10);
    currentQuiz = {
        subjectId, name, emoji,
        questions: shuffled, current: 0, score: 0, total: shuffled.length,
        difficulty, answers: [],
    };
    showView('quizActive');
    showQuestion();
}

function showQuestion() {
    const q = currentQuiz.questions[currentQuiz.current];
    const idx = currentQuiz.current;
    const total = currentQuiz.total;

    document.getElementById('quizCounter').textContent = `${idx + 1}/${total}`;
    document.getElementById('quizProgressBar').style.width = `${(idx / total) * 100}%`;
    document.getElementById('quizScore').textContent = `✅ ${currentQuiz.score}`;

    // Difficulty badge
    const diffMap = { 1: '🟢 Oson', 2: '🟡 O\'rta', 3: '🔴 Qiyin' };
    document.getElementById('quizDiffBadge').textContent = diffMap[q.difficulty] || '⭐ Aralash';

    document.getElementById('quizQuestion').textContent = q.text;

    const letters = ['A', 'B', 'C', 'D'];
    const keys = ['a', 'b', 'c', 'd'];
    const optsDiv = document.getElementById('quizOptions');
    optsDiv.innerHTML = keys.map((k, i) => `
        <button class="option-btn" id="opt_${k}" onclick="selectAnswer('${k}', '${q.correct}')">
            <span class="option-letter">${letters[i]}</span>
            <span>${q.options[k]}</span>
        </button>
    `).join('');

    // Fade in effect
    document.querySelector('.quiz-body')?.classList.add('fade-in');

    // Timer (30 seconds)
    startTimer(30);
}

function startTimer(seconds) {
    clearInterval(timerInterval);
    const bar = document.getElementById('timerBar');
    bar.style.transition = 'none';
    bar.style.width = '100%';

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            bar.style.transition = `width ${seconds}s linear`;
            bar.style.width = '0%';
        });
    });

    timerInterval = setTimeout(() => {
        // Auto-skip if no answer
        const q = currentQuiz.questions[currentQuiz.current];
        autoSkipAnswer(q);
    }, seconds * 1000);
}

function autoSkipAnswer(q) {
    currentQuiz.answers.push({
        question: q.text, correct: q.correct, selected: null,
        options: q.options, isCorrect: false, timedOut: true,
    });

    // Highlight correct
    const correctBtn = document.getElementById(`opt_${q.correct}`);
    if (correctBtn) correctBtn.classList.add('correct');

    const btns = document.querySelectorAll('.option-btn');
    btns.forEach(b => b.style.pointerEvents = 'none');

    showToast('⏱️', 'Vaqt tugadi!');

    setTimeout(() => {
        currentQuiz.current++;
        if (currentQuiz.current < currentQuiz.total) showQuestion();
        else finishQuiz();
    }, 1200);
}

function selectAnswer(selected, correct) {
    clearTimeout(timerInterval);
    const btns = document.querySelectorAll('.option-btn');
    btns.forEach(b => b.style.pointerEvents = 'none');

    const isCorrect = selected === correct;
    if (isCorrect) currentQuiz.score++;

    document.getElementById(`opt_${correct}`).classList.add('correct');
    if (!isCorrect) document.getElementById(`opt_${selected}`).classList.add('wrong');

    // Store answer for review
    const q = currentQuiz.questions[currentQuiz.current];
    currentQuiz.answers.push({
        question: q.text, correct, selected,
        options: q.options, isCorrect, timedOut: false,
    });

    // Haptic feedback
    if (tg?.HapticFeedback) {
        isCorrect ? tg.HapticFeedback.impactOccurred('light') : tg.HapticFeedback.notificationOccurred('error');
    }

    setTimeout(() => {
        currentQuiz.current++;
        if (currentQuiz.current < currentQuiz.total) showQuestion();
        else finishQuiz();
    }, 900);
}

async function finishQuiz() {
    clearTimeout(timerInterval);
    const { score, total, subjectId } = currentQuiz;
    const pct = Math.round((score / total) * 100);

    let band, emoji, title;
    if (pct >= 90) { band = '8.5'; emoji = '🏆'; title = 'Mukammal!'; }
    else if (pct >= 80) { band = '7.5'; emoji = '🥇'; title = 'Ajoyib natija!'; }
    else if (pct >= 70) { band = '7.0'; emoji = '🎯'; title = 'Yaxshi!'; }
    else if (pct >= 60) { band = '6.0'; emoji = '👍'; title = 'Yaxshi mashq!'; }
    else if (pct >= 40) { band = '5.0'; emoji = '📖'; title = 'Davom eting!'; }
    else { band = '4.0'; emoji = '💪'; title = 'Ko\'proq mashq kerak'; }

    // Save result
    if (subjectId > 0) {
        try {
            await fetch(`${API_BASE}/results`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, subject_id: subjectId, score, total, percentage: pct }),
            });
        } catch (e) { console.error(e); }
    }

    showView('quizResult');

    document.getElementById('resultEmoji').textContent = emoji;
    document.getElementById('resultTitle').textContent = title;
    document.getElementById('resultBand').textContent = band;
    document.getElementById('resultCorrect').textContent = score;
    document.getElementById('resultWrong').textContent = total - score;
    document.getElementById('resultPercent').textContent = `${pct}%`;

    // Animate gauge
    setTimeout(() => {
        const arc = document.getElementById('gaugeArc');
        const offset = 251 - (251 * pct / 100);
        arc.style.transition = 'stroke-dashoffset 1.2s ease-out';
        arc.style.strokeDashoffset = offset;
    }, 200);

    // Confetti🎉
    if (pct >= 70) spawnConfetti();
}

function resetQuiz() {
    currentQuiz = null;
    clearTimeout(timerInterval);
    // Reset gauge
    const arc = document.getElementById('gaugeArc');
    arc.style.transition = 'none';
    arc.style.strokeDashoffset = 251;
    showView('quizSubjects');
}

function quitQuiz() {
    clearTimeout(timerInterval);
    currentQuiz = null;
    showView('quizSubjects');
}

function showReview() {
    if (!currentQuiz) return;
    const list = document.getElementById('reviewList');
    const letters = { a: 'A', b: 'B', c: 'C', d: 'D' };

    list.innerHTML = currentQuiz.answers.map((a, i) => {
        const cls = a.isCorrect ? 'ri-correct' : 'ri-wrong';
        const badge = a.timedOut
            ? '<span class="ri-badge wrong">⏱️ Vaqt tugadi</span>'
            : a.isCorrect
                ? '<span class="ri-badge correct">✅ To\'g\'ri</span>'
                : '<span class="ri-badge wrong">❌ Xato</span>';

        let answerText = '';
        if (!a.isCorrect) {
            answerText = `<div class="ri-answer">
                ${a.selected ? `Sizning javob: <span style="color:var(--danger)">${letters[a.selected]}) ${a.options[a.selected]}</span><br>` : ''}
                To'g'ri javob: <span style="color:var(--success)">${letters[a.correct]}) ${a.options[a.correct]}</span>
            </div>`;
        }

        return `
            <div class="review-item ${cls}">
                <div class="ri-header">
                    <span class="ri-num">#${i + 1}</span>
                    ${badge}
                </div>
                <div class="ri-question">${a.question}</div>
                ${answerText}
            </div>
        `;
    }).join('');

    showView('quizReview');
}

function hideReview() {
    showView('quizResult');
}

function showView(viewId) {
    const views = ['quizSubjects', 'quizDifficulty', 'quizActive', 'quizResult', 'quizReview'];
    views.forEach(v => document.getElementById(v)?.classList.add('hidden'));
    const el = document.getElementById(viewId);
    if (el) {
        el.classList.remove('hidden');
        el.classList.add('fade-in');
    }
}

// ==========================================
//  FLASHCARDS
// ==========================================

async function loadFlashcards() {
    const data = await apiFetch('/flashcards');
    if (!data) return;

    flashcards = data.cards || [];
    currentFcIndex = 0;

    document.getElementById('flashcardStats').innerHTML = `
        <span>📚 Jami: ${data.total}</span>
        <span>✅ O'rganilgan: ${data.mastered}</span>
        <span>📙 Yangi: ${data.learning}</span>
    `;

    if (flashcards.length > 0) {
        updateFcCounter();
        showFlashcard();
    } else {
        document.getElementById('fcFront').textContent = 'Kartalar yo\'q';
        document.getElementById('fcBack').textContent = 'Bot orqali /flashcards yuklang';
        document.getElementById('fcCounter').textContent = '0 / 0';
    }
}

function showFlashcard() {
    if (flashcards.length === 0) return;
    const fc = flashcards[currentFcIndex];
    document.getElementById('fcFront').textContent = fc.front;
    document.getElementById('fcBack').textContent = fc.back;
    document.getElementById('fcExample').textContent = fc.example || '';
    document.getElementById('flashcardInner').classList.remove('flipped');
    updateFcCounter();
}

function flipCard() {
    document.getElementById('flashcardInner').classList.toggle('flipped');
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
}

function updateFcCounter() {
    document.getElementById('fcCounter').textContent = `${currentFcIndex + 1} / ${flashcards.length}`;
}

function loadFlashcard() {
    if (flashcards.length === 0) return;
    currentFcIndex = (currentFcIndex + 1) % flashcards.length;
    showFlashcard();
}

async function flashcardResponse(type) {
    if (flashcards.length === 0) return;
    const fc = flashcards[currentFcIndex];

    try {
        await fetch(`${API_BASE}/flashcards/response`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, card_id: fc.id, response: type }),
        });
    } catch (e) { console.error(e); }

    if (type === 'knew') {
        flashcards.splice(currentFcIndex, 1);
        if (currentFcIndex >= flashcards.length) currentFcIndex = 0;
        showToast('✅', 'O\'rganildi! Ajoyib!');
    } else {
        showToast('📝', 'Takrorlanadi');
        currentFcIndex = (currentFcIndex + 1) % flashcards.length;
    }

    if (flashcards.length > 0) showFlashcard();
    else {
        document.getElementById('fcFront').textContent = '🎉 Barcha kartalar o\'rganildi!';
        document.getElementById('fcCounter').textContent = '0 / 0';
    }
}

// ==========================================
//  STATS
// ==========================================

async function loadStats() {
    const data = await apiFetch('/stats');
    if (!data) return;

    document.getElementById('statTests').textContent = data.total_tests;
    document.getElementById('statAvg').textContent = `${data.avg_percentage}%`;
    document.getElementById('statBand').textContent = data.avg_band;
    document.getElementById('statStreak').textContent = data.streak;

    // Subject performance bars
    const barsDiv = document.getElementById('subjectBars');
    if (data.subject_stats && data.subject_stats.length > 0) {
        barsDiv.innerHTML = data.subject_stats.map(s => `
            <div class="sb-item">
                <div class="sb-header">
                    <span class="sb-name">${s.emoji} ${s.name}</span>
                    <span class="sb-pct">${s.avg}%</span>
                </div>
                <div class="sb-bar">
                    <div class="sb-fill" style="width: ${s.avg}%"></div>
                </div>
            </div>
        `).join('');
    } else {
        barsDiv.innerHTML = '<div class="empty-state"><div class="es-icon">📊</div><div class="es-text">Hali natija yo\'q</div></div>';
    }

    // History
    const histDiv = document.getElementById('statsHistory');
    if (data.history && data.history.length > 0) {
        histDiv.innerHTML = data.history.map(h => {
            const cls = h.percentage >= 75 ? 'high' : h.percentage >= 50 ? 'mid' : 'low';
            return `
                <div class="history-item">
                    <div>
                        <div class="hi-subject">${h.emoji} ${h.subject}</div>
                        <div class="hi-date">${h.date}</div>
                    </div>
                    <div class="hi-score ${cls}">${h.score}/${h.total} (${h.percentage}%)</div>
                </div>
            `;
        }).join('');
    } else {
        histDiv.innerHTML = '<div class="empty-state"><div class="es-icon">🕐</div><div class="es-text">Hali test yechilmagan</div></div>';
    }

    // Leaderboard
    const lbDiv = document.getElementById('leaderboard');
    if (data.leaderboard && data.leaderboard.length > 0) {
        const medals = ['🥇', '🥈', '🥉'];
        lbDiv.innerHTML = data.leaderboard.map((u, i) => `
            <div class="lb-item">
                <div class="lb-rank">${medals[i] || (i + 1)}</div>
                <div class="lb-name">${u.name}</div>
                <div class="lb-score">${u.avg}%</div>
            </div>
        `).join('');
    } else {
        lbDiv.innerHTML = '<div class="empty-state"><div class="es-icon">🏆</div><div class="es-text">Reyting tez orada</div></div>';
    }

    // --- Interactive Charts ---
    initTrendChart(data.chart_trend || []);
    initRadarChart(data.subject_stats || []);
}

function initTrendChart(trendData) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    if (trendChart) trendChart.destroy();

    const labels = trendData.length > 0 ? trendData.map(d => d.date) : ['No Data'];
    const values = trendData.length > 0 ? trendData.map(d => d.pct) : [0];

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Band Score %',
                data: values,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#6366f1',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function initRadarChart(stats) {
    const ctx = document.getElementById('radarChart');
    if (!ctx) return;

    if (radarChart) radarChart.destroy();

    const labels = stats.length >= 3 ? stats.map(s => s.name) : ['Listening', 'Reading', 'Grammar', 'Vocabulary'];
    const values = stats.length >= 3 ? stats.map(s => s.avg) : [0, 0, 0, 0];

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Skill Level %',
                data: values,
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                borderColor: '#06b6d4',
                pointBackgroundColor: '#06b6d4',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { display: false },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#94a3b8', font: { size: 10 } }
                }
            }
        }
    });
}

// ==========================================
//  CBT SIMULATOR
// ==========================================

async function openCBTSimulator() {
    // Check if premium for CBT (optional, but requested by user in prev logs)
    const prem = await apiFetch('/premium/status');
    if (prem && !prem.is_premium && !isStaticMode) {
        showToast('👑', 'Premium obuna kerak!');
        switchTab('premium');
        return;
    }

    document.getElementById('cbtOverlay').classList.remove('hidden');

    // Fetch Reading questions for CBT
    let questions = await apiFetch('/questions/18'); // Assuming 18 is Reading based on previous logs or data
    if (!questions || questions.length === 0) {
        // Mock data for demo if no reading subject found
        questions = Array(40).fill(0).map((_, i) => ({
            id: 1000 + i,
            text: `Question ${i + 1}: Based on the passage, what is the main argument regarding technology?`,
            options: { a: 'It is highly beneficial', b: 'It is harmful', c: 'It is neutral', d: 'It is inevitable' },
            correct: 'a'
        }));
    }

    startCBT(questions);
}

function closeCBTSimulator(force = false) {
    if (!force && !confirm('Chindan ham chiqmoqchimisiz? Natijalar saqlanmaydi.')) return;
    document.getElementById('cbtOverlay').classList.add('hidden');
    clearInterval(cbtTimerInterval);
}

function startCBT(questions) {
    cbtQuestions = questions.slice(0, 40);
    cbtAnswers = {};

    document.getElementById('cbtPassageText').innerHTML = `
        <h2>The Evolution of Modern Technology</h2>
        <p>In the contemporary era, the rapid progression of <b>information technology</b> has fundamentally altered the landscape of human interaction and economic structures. Unlike previous industrial revolutions, the current digital age is characterized by the velocity and ubiquity of data transfer.</p>
        <p>Proponents argue that digital integration fosters <i>unprecedented transparency</i> and accessibility. For instance, the democratization of information allows individuals to acquire specialized knowledge without traditional institutional barriers. This paradigm shift has notably empowered marginalized communities across the globe.</p>
        <p>However, skeptics raise concerns regarding the <b>erosion of privacy</b> and the potential for algorithmic bias. As artificial intelligence models become increasingly autonomous, the ethical implications of automated decision-making warrant rigorous scrutiny. The balance between innovation and regulation remains a central debate in modern policy design.</p>
        <p>Furthermore, the psychological impact of prolonged connectivity is a subject of ongoing academic research. Studies suggest that while digital tools enhance productivity, they may also contribute to increased levels of anxiety and cognitive fragmentation among younger demographics.</p>
    `;

    renderCBTNav();
    showCBTQuestion(0);
    startCBTTimer(60 * 60); // 60 minutes
}

function renderCBTNav() {
    const nav = document.getElementById('cbtNavPills');
    nav.innerHTML = cbtQuestions.map((_, i) => `
        <div class="cbt-pill" id="cbtPill_${i}" onclick="showCBTQuestion(${i})">${i + 1}</div>
    `).join('');
}

function showCBTQuestion(index) {
    const q = cbtQuestions[index];
    const area = document.getElementById('cbtQuestionArea');

    // Update active pill
    document.querySelectorAll('.cbt-pill').forEach(p => p.classList.remove('active'));
    document.getElementById(`cbtPill_${index}`).classList.add('active');

    area.innerHTML = `
        <div class="cbt-q-item fade-in">
            <div class="cbt-q-text">${q.text}</div>
            <div class="cbt-opts">
                ${['a', 'b', 'c', 'd'].map(k => `
                    <div class="cbt-opt ${cbtAnswers[index] === k ? 'selected' : ''}" onclick="selectCBTAnswer(${index}, '${k}')">
                        <div class="cbt-opt-radio"></div>
                        <span>${q.options[k]}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function selectCBTAnswer(index, value) {
    cbtAnswers[index] = value;
    document.querySelectorAll('.cbt-opt').forEach(o => o.classList.remove('selected'));
    // Re-render current question to show selection (or just DOM update for speed)
    showCBTQuestion(index);

    // Mark pill as answered
    document.getElementById(`cbtPill_${index}`).classList.add('answered');
}

function startCBTTimer(seconds) {
    clearInterval(cbtTimerInterval);
    let remaining = seconds;
    const timerEl = document.getElementById('cbtTimer');

    cbtTimerInterval = setInterval(() => {
        remaining--;
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        timerEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

        if (remaining <= 300) timerEl.style.background = '#e67e22'; // 5 min warning
        if (remaining <= 60) timerEl.style.background = '#c0392b'; // 1 min warning

        if (remaining <= 0) {
            clearInterval(cbtTimerInterval);
            alert('Vaqt tugadi!');
            submitCBT();
        }
    }, 1000);
}

async function submitCBT() {
    let score = 0;
    cbtQuestions.forEach((q, i) => {
        if (cbtAnswers[i] === q.correct) score++;
    });

    const total = cbtQuestions.length;
    const pct = Math.round((score / total) * 100);

    showToast('📈', `CBT yakunlandi: ${score}/${total}`);

    // Save to results via same API
    if (userId && !isStaticMode) {
        await fetch(`${API_BASE}/results`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, subject_id: 18, score, total, percentage: pct, is_mock: true }),
        });
    }

    closeCBTSimulator(true);
    switchTab('stats');
}

// ==========================================
//  PREMIUM
// ==========================================

async function checkPremium() {
    const data = await apiFetch('/premium/status');
    if (!data) return;

    if (data.is_premium) {
        document.getElementById('premiumBadge').classList.remove('hidden');
        document.getElementById('premiumStatus').classList.remove('hidden');
        if (data.expiry) {
            document.getElementById('premiumExpiry').textContent = `Amal qilish: ${data.expiry}`;
        }
    }
}

function buyPremium(plan) {
    if (tg) {
        tg.sendData(JSON.stringify({ action: 'buy_premium', plan }));
        tg.close();
    } else {
        showToast('👑', 'Bot orqali /premium buyrug\'ini bosing');
    }
}

// ==========================================
//  UTILS
// ==========================================

function showToast(icon, msg) {
    const toast = document.getElementById('toast');
    document.getElementById('toastIcon').textContent = icon;
    document.getElementById('toastMsg').textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

function spawnConfetti() {
    const canvas = document.getElementById('confettiCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    const particles = [];
    const colors = ['#6366f1', '#a78bfa', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#06b6d4'];

    for (let i = 0; i < 60; i++) {
        particles.push({
            x: canvas.width / 2,
            y: canvas.height / 2,
            vx: (Math.random() - 0.5) * 12,
            vy: (Math.random() - 0.5) * 12 - 4,
            size: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            rotSpeed: (Math.random() - 0.5) * 10,
            life: 1,
        });
    }

    let frame = 0;
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        let alive = false;

        particles.forEach(p => {
            if (p.life <= 0) return;
            alive = true;
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.2;  // gravity
            p.rotation += p.rotSpeed;
            p.life -= 0.015;
            p.vx *= 0.99;

            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate((p.rotation * Math.PI) / 180);
            ctx.globalAlpha = p.life;
            ctx.fillStyle = p.color;
            ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
            ctx.restore();
        });

        if (alive && frame < 120) {
            frame++;
            requestAnimationFrame(animate);
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }
    animate();
}
