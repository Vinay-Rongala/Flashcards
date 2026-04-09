// Language Flashcards — Frontend Application

// ============================================================
// CONFIGURATION
// ============================================================
const CONFIG = {
    // Change YOUR_BACKEND_URL to your Render backend URL when deploying to production
    API_BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:8000' 
        : 'https://flashcards-b935.onrender.com',
    API_TIMEOUT: 120000,
    DEBUG_MODE: true
};

// ============================================================
// STORAGE KEYS
// ============================================================
const STORAGE_KEYS = {
    WORD_PAIRS: 'flashcard_word_pairs',
    SENTENCES: 'flashcard_sentences',
    MCQ_QUESTIONS: 'flashcard_mcq_questions',
    API_KEY: 'groq_api_key'
};

// ============================================================
// APP STATE
// ============================================================
let wordPairs = [];
let sentences = [];
let mcqQuestions = [];
let currentQuizIndex = 0;
let quizScore = 0;
let selectedFiles = [];
let groqApiKey = '';
let userAnswers = [];

// ============================================================
// DOM ELEMENTS
// ============================================================
const elements = {
    // Modal
    apiKeyModal: document.getElementById('apiKeyModal'),
    apiKeyInput: document.getElementById('apiKeyInput'),
    apiKeySubmit: document.getElementById('apiKeySubmit'),
    toggleApiKeyVisibility: document.getElementById('toggleApiKeyVisibility'),
    // Main app
    mainApp: document.getElementById('mainApp'),
    changeKeyBtn: document.getElementById('changeKeyBtn'),
    wordCount: document.getElementById('wordCount'),
    resetBtn: document.getElementById('resetBtn'),
    navTabs: document.querySelectorAll('.nav-tab'),
    tabContents: document.querySelectorAll('.tab-content'),
    statusMessage: document.getElementById('statusMessage'),
    // Upload
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    uploadBtn: document.getElementById('uploadBtn'),
    uploadStatus: document.getElementById('uploadStatus'),
    selectedFiles: document.getElementById('selectedFiles'),
    // Flashcards
    flashcardContainer: document.getElementById('flashcardContainer'),
    // Sentences
    sentencesContainer: document.getElementById('sentencesContainer'),
    generateSentencesBtn: document.getElementById('generateSentencesBtn'),
    // MCQ
    quizContainer: document.getElementById('quizContainer'),
    startQuizBtn: document.getElementById('startQuizBtn'),
    resetQuizBtn: document.getElementById('resetQuizBtn'),
    currentScore: document.getElementById('currentScore'),
    totalScore: document.getElementById('totalScore'),
    questionNumber: document.getElementById('questionNumber'),
    totalQuestions: document.getElementById('totalQuestions'),
    quizHeader: document.getElementById('quizHeader')
};

// ============================================================
// INITIALISATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadFromStorage();
    setupModalListeners();
    setupEventListeners();

    // Show modal if no key is saved, else show main app
    if (groqApiKey) {
        showMainApp();
    } else {
        showModal();
    }
});

// ============================================================
// API KEY MODAL
// ============================================================
function showModal() {
    elements.apiKeyModal.classList.add('active');
    elements.mainApp.style.display = 'none';
    elements.apiKeyInput.focus();
}

function showMainApp() {
    elements.apiKeyModal.classList.remove('active');
    elements.mainApp.style.display = 'block';
    updateUI();
}

function setupModalListeners() {
    // Enable submit only when input is non-empty
    elements.apiKeyInput.addEventListener('input', () => {
        const val = elements.apiKeyInput.value.trim();
        elements.apiKeySubmit.disabled = val.length === 0;
    });

    // Submit on button click
    elements.apiKeySubmit.addEventListener('click', saveApiKey);

    // Submit on Enter
    elements.apiKeyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !elements.apiKeySubmit.disabled) {
            saveApiKey();
        }
    });

    // Toggle password visibility
    elements.toggleApiKeyVisibility.addEventListener('click', () => {
        const isPassword = elements.apiKeyInput.type === 'password';
        elements.apiKeyInput.type = isPassword ? 'text' : 'password';
        elements.toggleApiKeyVisibility.textContent = isPassword ? '🙈' : '👁';
    });
}

function saveApiKey() {
    const key = elements.apiKeyInput.value.trim();
    if (!key) return;
    groqApiKey = key;
    localStorage.setItem(STORAGE_KEYS.API_KEY, key);
    elements.apiKeyInput.value = '';            // don't leave it visible
    elements.apiKeyInput.type = 'password';
    elements.toggleApiKeyVisibility.textContent = '👁';
    elements.apiKeySubmit.disabled = true;
    showMainApp();
    showStatusMessage('API key saved successfully!', 'success');
}

// ============================================================
// STORAGE
// ============================================================
function loadFromStorage() {
    try {
        groqApiKey = localStorage.getItem(STORAGE_KEYS.API_KEY) || '';
        wordPairs = JSON.parse(localStorage.getItem(STORAGE_KEYS.WORD_PAIRS) || '[]');
        sentences = JSON.parse(localStorage.getItem(STORAGE_KEYS.SENTENCES) || '[]');
        mcqQuestions = JSON.parse(localStorage.getItem(STORAGE_KEYS.MCQ_QUESTIONS) || '[]');
    } catch (error) {
        console.error('Error loading from storage:', error);
        wordPairs = [];
        sentences = [];
        mcqQuestions = [];
    }
}

function saveToStorage() {
    try {
        localStorage.setItem(STORAGE_KEYS.WORD_PAIRS, JSON.stringify(wordPairs));
        localStorage.setItem(STORAGE_KEYS.SENTENCES, JSON.stringify(sentences));
        localStorage.setItem(STORAGE_KEYS.MCQ_QUESTIONS, JSON.stringify(mcqQuestions));
    } catch (error) {
        console.error('Error saving to storage:', error);
        if (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
            showStatusMessage('Storage quota exceeded. Some data may not be saved.', 'error');
        }
        throw error;
    }
}

// ============================================================
// FETCH HELPER — always attaches the Groq API key header
// ============================================================
async function apiFetch(endpoint, options = {}) {
    const headers = {
        ...(options.headers || {}),
        'X-Groq-Api-Key': groqApiKey
    };
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });
    return response;
}

// ============================================================
// AUDIO HELPERS
// ============================================================
function playText(event, text, lang) {
    if (event) {
        event.stopPropagation();
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    window.speechSynthesis.speak(utterance);
}

// ============================================================
// UI HELPERS
// ============================================================
function updateUI() {
    elements.wordCount.textContent = wordPairs.length;
    elements.generateSentencesBtn.disabled = wordPairs.length === 0;
    elements.startQuizBtn.disabled = wordPairs.length < 4;
    renderFlashcards();
    renderSentences();
    updateQuizHeader();
}

function switchTab(tabName) {
    elements.navTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-section`);
    });
    hideStatusMessage();
}

function showStatusMessage(message, type = 'info') {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = `status-message ${type}`;
    elements.statusMessage.classList.remove('hidden');
    setTimeout(hideStatusMessage, 5000);
}

function hideStatusMessage() {
    elements.statusMessage.classList.add('hidden');
}

function showLoading(container) {
    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p class="loading-text">Loading...</p>
        </div>
    `;
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ============================================================
// EVENT LISTENERS
// ============================================================
function setupEventListeners() {
    // Navigation
    elements.navTabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Change key button
    elements.changeKeyBtn.addEventListener('click', () => {
        elements.apiKeyInput.value = '';
        elements.apiKeySubmit.disabled = true;
        showModal();
    });

    // Reset all data
    elements.resetBtn.addEventListener('click', resetAllData);

    // File upload
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.uploadBtn.addEventListener('click', uploadFile);
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('dragleave', handleDragLeave);
    elements.uploadArea.addEventListener('drop', handleDrop);

    // Sentences
    elements.generateSentencesBtn.addEventListener('click', generateSentences);

    // Quiz
    elements.startQuizBtn.addEventListener('click', startQuiz);
    elements.resetQuizBtn.addEventListener('click', resetQuiz);
}

// ============================================================
// RESET
// ============================================================
function resetAllData() {
    if (confirm('Are you sure you want to reset all data? This cannot be undone.')) {
        wordPairs = [];
        sentences = [];
        mcqQuestions = [];
        userAnswers = [];
        resetQuiz();
        saveToStorage();
        updateUI();
        showStatusMessage('All data has been reset', 'info');
    }
}

// ============================================================
// FILE HANDLING & UPLOAD
// ============================================================
function handleDragOver(e) {
    e.preventDefault();
    elements.uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    elements.uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    elements.uploadArea.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) selectFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) selectFiles(files);
}

function selectFiles(files) {
    files.forEach(file => {
        const isDuplicate = selectedFiles.some(f => f.name === file.name && f.size === file.size);
        if (!isDuplicate) selectedFiles.push(file);
    });
    renderSelectedFiles();
    updateUploadButton();
}

function removeSelectedFile(index) {
    selectedFiles.splice(index, 1);
    renderSelectedFiles();
    updateUploadButton();
}

function renderSelectedFiles() {
    if (selectedFiles.length === 0) {
        elements.selectedFiles.classList.remove('active');
        elements.selectedFiles.innerHTML = '';
        elements.uploadArea.querySelector('.upload-text').textContent = 'Drag & drop your files here';
        elements.uploadArea.querySelector('.upload-subtext').textContent = 'or click to browse (multiple files supported)';
        return;
    }
    elements.selectedFiles.classList.add('active');
    elements.uploadArea.querySelector('.upload-text').textContent =
        `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;
    elements.selectedFiles.innerHTML = selectedFiles.map((file, index) => `
        <div class="selected-file-item">
            <div class="selected-file-info">
                <span class="selected-file-name">${escapeHtml(file.name)}</span>
                <span class="selected-file-size">${formatFileSize(file.size)}</span>
            </div>
            <button class="selected-file-remove" onclick="removeSelectedFile(${index})" title="Remove file">×</button>
        </div>
    `).join('');
}

function updateUploadButton() {
    elements.uploadBtn.disabled = selectedFiles.length === 0;
}

async function uploadFile() {
    if (selectedFiles.length === 0) return;

    showUploadStatus(true);
    hideStatusMessage();

    let allWordPairs = [];
    let successCount = 0;
    let errorCount = 0;

    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        updateUploadStatus(`Extracting from ${escapeHtml(file.name)} (${i + 1}/${selectedFiles.length})...`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await apiFetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
                throw new Error(detail || 'Upload failed');
            }

            // Merge, avoiding duplicates
            data.word_pairs.forEach(newPair => {
                const isDuplicate = allWordPairs.some(existing =>
                    existing.english.toLowerCase() === newPair.english.toLowerCase() &&
                    existing.foreign.toLowerCase() === newPair.foreign.toLowerCase()
                );
                if (!isDuplicate) allWordPairs.push(newPair);
            });
            successCount++;

        } catch (error) {
            errorCount++;
            console.error(`Error uploading ${file.name}:`, error);
            showStatusMessage(`Error on ${file.name}: ${error.message}`, 'error');
        }
    }

    if (allWordPairs.length > 0) {
        // Merge with existing stored pairs (also deduplicating)
        allWordPairs.forEach(newPair => {
            const isDuplicate = wordPairs.some(existing =>
                existing.english.toLowerCase() === newPair.english.toLowerCase() &&
                existing.foreign.toLowerCase() === newPair.foreign.toLowerCase()
            );
            if (!isDuplicate) wordPairs.push(newPair);
        });
        saveToStorage();
        updateUI();

        const msg = successCount === selectedFiles.length
            ? `✅ Extracted ${allWordPairs.length} word pairs from ${successCount} file(s)!`
            : `⚠️ Extracted ${allWordPairs.length} pairs from ${successCount} file(s). ${errorCount} failed.`;
        showStatusMessage(msg, errorCount > 0 ? 'warning' : 'success');
    } else if (errorCount === 0) {
        showStatusMessage('No word pairs found in the selected file(s).', 'error');
    }

    // Reset upload UI
    elements.fileInput.value = '';
    selectedFiles = [];
    renderSelectedFiles();
    updateUploadButton();
    showUploadStatus(false);
}

function showUploadStatus(showing) {
    elements.uploadStatus.classList.toggle('active', showing);
    if (showing) {
        elements.uploadStatus.innerHTML = `
            <div class="progress"><div class="progress-bar"></div></div>
            <p id="uploadStatusText">Extracting word pairs with AI...</p>
        `;
    }
}

function updateUploadStatus(message) {
    const el = document.getElementById('uploadStatusText');
    if (el) el.textContent = message;
}

// ============================================================
// FLASHCARDS
// ============================================================
function renderFlashcards() {
    if (wordPairs.length === 0) {
        elements.flashcardContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🃏</span>
                <p>No flashcards yet</p>
                <p class="empty-hint">Upload a document to get started</p>
            </div>
        `;
        return;
    }
    elements.flashcardContainer.innerHTML = wordPairs.map(pair => `
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <span>${escapeHtml(pair.english)}</span>
                    <button class="speaker-btn" data-text="${escapeHtml(pair.english)}" data-lang="en-US"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                </div>
                <div class="flashcard-back">
                    <span>${escapeHtml(pair.foreign)}</span>
                    <button class="speaker-btn" data-text="${escapeHtml(pair.foreign)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                </div>
            </div>
        </div>
    `).join('');

    elements.flashcardContainer.querySelectorAll('.speaker-btn').forEach(btn => {
        btn.addEventListener('click', (e) => playText(e, btn.dataset.text, btn.dataset.lang));
    });
}

// ============================================================
// SENTENCES
// ============================================================
async function generateSentences() {
    if (wordPairs.length === 0) return;

    showLoading(elements.sentencesContainer);
    hideStatusMessage();

    try {
        const response = await apiFetch('/sentences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_pairs: wordPairs })
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
            throw new Error(detail || 'Failed to generate sentences');
        }

        sentences = data.sentences;
        saveToStorage();
        renderSentences();
        showStatusMessage(`Generated ${data.count} example sentences!`, 'success');

    } catch (error) {
        showStatusMessage(error.message, 'error');
        renderSentences();
    }
}

function renderSentences() {
    if (sentences.length === 0) {
        elements.sentencesContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📝</span>
                <p>No sentences yet</p>
                <p class="empty-hint">Upload a document and click Generate Sentences</p>
            </div>
        `;
        return;
    }
    elements.sentencesContainer.innerHTML = sentences.map(item => `
        <div class="sentence-card">
            <div class="sentence-word">
                <span class="word-pair highlight">
                    ${escapeHtml(item.english)}
                    <button class="speaker-btn mini" data-text="${escapeHtml(item.english)}" data-lang="en-US"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                </span>
                <span class="word-separator">→</span>
                <span class="word-pair highlight">
                    ${escapeHtml(item.foreign)}
                    <button class="speaker-btn mini" data-text="${escapeHtml(item.foreign)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                </span>
            </div>
            <p class="sentence-text en">
                <button class="speaker-btn mini" data-text="${escapeHtml(item.english_sentence)}" data-lang="en-US"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                ${escapeHtml(item.english_sentence)}
            </p>
            <p class="sentence-text foreign">
                <button class="speaker-btn mini" data-text="${escapeHtml(item.foreign_sentence)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                ${escapeHtml(item.foreign_sentence)}
            </p>
        </div>
    `).join('');

    elements.sentencesContainer.querySelectorAll('.speaker-btn').forEach(btn => {
        btn.addEventListener('click', (e) => playText(e, btn.dataset.text, btn.dataset.lang));
    });
}

// ============================================================
// MCQ QUIZ
// ============================================================
async function startQuiz() {
    if (wordPairs.length < 4) return;

    showLoading(elements.quizContainer);
    elements.quizHeader.style.display = 'none';

    try {
        const response = await apiFetch('/mcq', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_pairs: wordPairs })
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
            throw new Error(detail || 'Failed to generate quiz');
        }

        mcqQuestions = data.questions;
        currentQuizIndex = 0;
        quizScore = 0;
        userAnswers = [];
        saveToStorage();

        elements.quizHeader.style.display = 'flex';
        elements.startQuizBtn.classList.add('hidden');
        elements.resetQuizBtn.classList.remove('hidden');

        renderQuestion();
        showStatusMessage('Quiz started! Good luck! 🎯', 'info');

    } catch (error) {
        showStatusMessage(error.message, 'error');
        elements.quizContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">❓</span>
                <p>Failed to load quiz</p>
                <p class="empty-hint">${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function renderQuestion() {
    updateQuizHeader();

    if (currentQuizIndex >= mcqQuestions.length) {
        showQuizResult();
        return;
    }

    const question = mcqQuestions[currentQuizIndex];

    elements.quizContainer.innerHTML = `
        <div class="quiz-question">
            <p class="question-text">
                <button class="speaker-btn" data-text="${escapeHtml(question.question)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                ${escapeHtml(question.question)}
            </p>
            <div class="quiz-options">
                ${question.options.map(option => `
                    <button class="quiz-option"
                        data-option="${escapeHtml(option)}"
                        data-correct="${escapeHtml(question.correct)}">
                        ${escapeHtml(option)}
                        <span class="speaker-btn option-speaker" data-text="${escapeHtml(option)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></span>
                    </button>
                `).join('')}
            </div>
        </div>
    `;

    // Attach listeners dynamically to avoid HTML quote escaping conflicts
    const optionBtns = elements.quizContainer.querySelectorAll('.quiz-option');
    optionBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (e.target.closest('.speaker-btn')) return; // handled below
            selectOption(this.dataset.option, this.dataset.correct, this);
        });
    });

    elements.quizContainer.querySelectorAll('.speaker-btn').forEach(btn => {
        btn.addEventListener('click', (e) => playText(e, btn.dataset.text, btn.dataset.lang));
    });
}

function selectOption(selected, correct, button) {
    const options = elements.quizContainer.querySelectorAll('.quiz-option');
    options.forEach(opt => opt.disabled = true);

    userAnswers.push({
        question: mcqQuestions[currentQuizIndex].question,
        selected: selected,
        correct: correct,
        isCorrect: selected === correct
    });

    if (selected === correct) {
        button.classList.add('correct');
        quizScore++;
        showStatusMessage('✅ Correct!', 'success');
    } else {
        button.classList.add('incorrect');
        // Highlight the correct answer too
        options.forEach(opt => {
            if (opt.textContent.trim() === correct) {
                opt.classList.add('correct');
            }
        });
        showStatusMessage(`❌ Incorrect. The answer was: ${correct}`, 'error');
    }

    // Form the full sentence with the correct answer and remove the hint
    const fullSentence = mcqQuestions[currentQuizIndex].question
        .replace(/_____\s*\([^)]+\)/, correct)
        .replace(/_____/, correct);
    
    // Read out the completed sentence aloud
    playText(null, fullSentence, 'de-DE');

    setTimeout(() => {
        currentQuizIndex++;
        renderQuestion();
    }, 2500);
}

function showQuizResult() {
    const percentage = Math.round((quizScore / mcqQuestions.length) * 100);
    let emoji, message;
    if (percentage === 100) { emoji = '🏆'; message = 'Perfect score!'; }
    else if (percentage >= 80) { emoji = '🌟'; message = 'Excellent work!'; }
    else if (percentage >= 60) { emoji = '👍'; message = 'Good job!'; }
    else if (percentage >= 40) { emoji = '📚'; message = 'Keep practicing!'; }
    else { emoji = '💪'; message = "Don't give up!"; }

    elements.quizContainer.innerHTML = `
        <div class="quiz-result">
            <div class="result-emoji">${emoji}</div>
            <div class="result-score">${quizScore} / ${mcqQuestions.length}</div>
            <div class="result-percentage">${percentage}%</div>
            <div class="result-message">${message}</div>
            
            <div class="quiz-history-container">
                <hr style="margin: 2rem 0; opacity: 0.1;">
                <h3 class="quiz-history-title">Quiz Review</h3>
                <div class="quiz-history-list">
                    ${userAnswers.map((ans, idx) => `
                        <div class="history-item ${ans.isCorrect ? 'history-correct' : 'history-incorrect'}">
                            <p class="history-q">
                                <strong>Q${idx + 1}:</strong> 
                                <button class="speaker-btn mini" data-text="${escapeHtml(ans.question)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                                ${escapeHtml(ans.question)}
                            </p>
                            <p class="history-a">Your answer: 
                                <button class="speaker-btn mini" data-text="${escapeHtml(ans.selected)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                                <span class="${ans.isCorrect ? 'text-success' : 'text-danger'}">${escapeHtml(ans.selected)}</span>
                            </p>
                            ${!ans.isCorrect ? `<p class="history-c">Correct answer: 
                                <button class="speaker-btn mini" data-text="${escapeHtml(ans.correct)}" data-lang="de-DE"><img src="volume.png" class="speaker-icon-img" alt="Listen" /></button>
                                <span class="text-success">${escapeHtml(ans.correct)}</span></p>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    setTimeout(() => {
        elements.quizContainer.querySelectorAll('.speaker-btn').forEach(btn => {
            btn.addEventListener('click', (e) => playText(e, btn.dataset.text, btn.dataset.lang));
        });
    }, 0);
}

function updateQuizHeader() {
    elements.currentScore.textContent = quizScore;
    elements.totalScore.textContent = mcqQuestions.length;
    elements.questionNumber.textContent = currentQuizIndex + 1;
    elements.totalQuestions.textContent = mcqQuestions.length;
}

function resetQuiz() {
    currentQuizIndex = 0;
    quizScore = 0;
    userAnswers = [];
    mcqQuestions = [];
    elements.startQuizBtn.classList.remove('hidden');
    elements.resetQuizBtn.classList.add('hidden');
    elements.quizHeader.style.display = 'none';
    elements.quizContainer.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">❓</span>
            <p>No quiz ready</p>
            <p class="empty-hint">Need at least 4 words to start a quiz</p>
        </div>
    `;
    saveToStorage();
    updateUI();
}
