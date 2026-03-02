// Language Flashcards - Frontend Application
// python -m http.server 3000
// uvicorn main:app --reload --port 8000
// ============================================
// CONFIGURATION - Easy to change for deployment
// ============================================
const CONFIG = {
    // Backend API URL - Change this when deploying to production
    // Local development: http://localhost:8000
    // Production example: https://your-app.onrender.com
    API_BASE_URL: 'http://127.0.0.1:8000',

    // API request timeout in milliseconds
    API_TIMEOUT: 120000, // 2 minutes

    // Whether to show detailed error messages in console
    DEBUG_MODE: true
};

// ============================================
// STORAGE KEYS
// ============================================
const STORAGE_KEYS = {
    WORD_PAIRS: 'flashcard_word_pairs',
    SENTENCES: 'flashcard_sentences',
    MCQ_QUESTIONS: 'flashcard_mcq_questions'
};

// State
let wordPairs = [];
let sentences = [];
let mcqQuestions = [];
let currentQuizIndex = 0;
let quizScore = 0;
let selectedFiles = []; // Changed to array for multiple files

// DOM Elements
const elements = {
    wordCount: document.getElementById('wordCount'),
    resetBtn: document.getElementById('resetBtn'),
    navTabs: document.querySelectorAll('.nav-tab'),
    tabContents: document.querySelectorAll('.tab-content'),
    statusMessage: document.getElementById('statusMessage'),
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    uploadBtn: document.getElementById('uploadBtn'),
    uploadStatus: document.getElementById('uploadStatus'),
    selectedFiles: document.getElementById('selectedFiles'),
    flashcardContainer: document.getElementById('flashcardContainer'),
    sentencesContainer: document.getElementById('sentencesContainer'),
    generateSentencesBtn: document.getElementById('generateSentencesBtn'),
    quizContainer: document.getElementById('quizContainer'),
    startQuizBtn: document.getElementById('startQuizBtn'),
    resetQuizBtn: document.getElementById('resetQuizBtn'),
    currentScore: document.getElementById('currentScore'),
    totalScore: document.getElementById('totalScore'),
    questionNumber: document.getElementById('questionNumber'),
    totalQuestions: document.getElementById('totalQuestions'),
    quizHeader: document.getElementById('quizHeader')
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadFromStorage();
    setupEventListeners();
    updateUI();
});

// Setup Event Listeners
function setupEventListeners() {
    // Navigation tabs
    elements.navTabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Reset button
    elements.resetBtn.addEventListener('click', resetAllData);

    // File upload
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.uploadBtn.addEventListener('click', uploadFile);

    // Drag and drop
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('dragleave', handleDragLeave);
    elements.uploadArea.addEventListener('drop', handleDrop);

    // Generate sentences
    elements.generateSentencesBtn.addEventListener('click', generateSentences);

    // Quiz controls
    elements.startQuizBtn.addEventListener('click', startQuiz);
    elements.resetQuizBtn.addEventListener('click', resetQuiz);
}

// Load data from localStorage
function loadFromStorage() {
    try {
        const savedPairs = localStorage.getItem(STORAGE_KEYS.WORD_PAIRS);
        const savedSentences = localStorage.getItem(STORAGE_KEYS.SENTENCES);
        const savedMCQ = localStorage.getItem(STORAGE_KEYS.MCQ_QUESTIONS);

        wordPairs = savedPairs ? JSON.parse(savedPairs) : [];
        sentences = savedSentences ? JSON.parse(savedSentences) : [];
        mcqQuestions = savedMCQ ? JSON.parse(savedMCQ) : [];
    } catch (error) {
        console.error('Error loading from storage:', error);
        wordPairs = [];
        sentences = [];
        mcqQuestions = [];
    }
}

// Save data to localStorage
function saveToStorage() {
    try {
        localStorage.setItem(STORAGE_KEYS.WORD_PAIRS, JSON.stringify(wordPairs));
        localStorage.setItem(STORAGE_KEYS.SENTENCES, JSON.stringify(sentences));
        localStorage.setItem(STORAGE_KEYS.MCQ_QUESTIONS, JSON.stringify(mcqQuestions));
    } catch (error) {
        console.error('Error saving to storage:', error);
        // Show user-friendly message for quota exceeded
        if (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
            showStatusMessage('Storage quota exceeded. Some data may not be saved.', 'error');
        }
        throw error; // Re-throw to let caller handle it if needed
    }
}

// Update UI
function updateUI() {
    elements.wordCount.textContent = wordPairs.length;

    // Enable/disable buttons based on word pairs
    elements.generateSentencesBtn.disabled = wordPairs.length === 0;
    elements.startQuizBtn.disabled = wordPairs.length < 4;

    // Update flashcards
    renderFlashcards();

    // Update sentences
    renderSentences();

    // Update quiz UI
    updateQuizHeader();
}

// Switch tabs
function switchTab(tabName) {
    elements.navTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-section`);
    });

    hideStatusMessage();
}

// Show status message
function showStatusMessage(message, type = 'info') {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = `status-message ${type}`;
    elements.statusMessage.classList.remove('hidden');

    setTimeout(() => {
        hideStatusMessage();
    }, 5000);
}

// Hide status message
function hideStatusMessage() {
    elements.statusMessage.classList.add('hidden');
}

// Reset all data
function resetAllData() {
    if (confirm('Are you sure you want to reset all data? This cannot be undone.')) {
        wordPairs = [];
        sentences = [];
        mcqQuestions = [];
        resetQuiz();
        saveToStorage();
        updateUI();
        showStatusMessage('All data has been reset', 'info');
    }
}

// File handling
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
    if (files.length > 0) {
        selectFiles(files);
    }
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        selectFiles(files);
    }
}

function selectFiles(files) {
    // Add files to the selected files array
    files.forEach(file => {
        // Check if file is already selected (by name and size)
        const isDuplicate = selectedFiles.some(f =>
            f.name === file.name && f.size === file.size
        );
        if (!isDuplicate) {
            selectedFiles.push(file);
        }
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
    elements.uploadArea.querySelector('.upload-text').textContent = `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;

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

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// Upload file
async function uploadFile() {
    if (selectedFiles.length === 0) return;

    showUploadStatus(true);
    hideStatusMessage();

    let allWordPairs = [];
    let successCount = 0;
    let errorCount = 0;

    // Upload files sequentially
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        updateUploadStatus(`Extracting from ${escapeHtml(file.name)} (${i + 1}/${selectedFiles.length})...`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Upload failed');
            }

            // Merge word pairs from this file
            // Avoid duplicates by checking if the word pair already exists
            data.word_pairs.forEach(newPair => {
                const isDuplicate = allWordPairs.some(existingPair =>
                    existingPair.english.toLowerCase() === newPair.english.toLowerCase() &&
                    existingPair.foreign.toLowerCase() === newPair.foreign.toLowerCase()
                );
                if (!isDuplicate) {
                    allWordPairs.push(newPair);
                }
            });

            successCount++;

        } catch (error) {
            errorCount++;
            console.error(`Error uploading ${file.name}:`, error);
        }
    }

    // Update word pairs with combined results
    if (allWordPairs.length > 0) {
        wordPairs = [...wordPairs, ...allWordPairs];
        saveToStorage();
        updateUI();

        const message = successCount === selectedFiles.length
            ? `Successfully extracted ${allWordPairs.length} word pairs from ${successCount} file(s)!`
            : `Extracted ${allWordPairs.length} word pairs from ${successCount} file(s). ${errorCount} file(s) failed.`;
        showStatusMessage(message, errorCount > 0 ? 'warning' : 'success');
    } else {
        showStatusMessage(`No word pairs could be extracted from the selected files.`, 'error');
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
    const statusText = document.getElementById('uploadStatusText');
    if (statusText) {
        statusText.textContent = message;
    }
}

// Render flashcards
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

    elements.flashcardContainer.innerHTML = wordPairs.map((pair, index) => `
        <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div class="flashcard-inner">
                <div class="flashcard-front">${escapeHtml(pair.english)}</div>
                <div class="flashcard-back">${escapeHtml(pair.foreign)}</div>
            </div>
        </div>
    `).join('');
}

// Generate sentences
async function generateSentences() {
    if (wordPairs.length === 0) return;

    showLoading(elements.sentencesContainer);
    hideStatusMessage();

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/sentences`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_pairs: wordPairs })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate sentences');
        }

        sentences = data.sentences;
        saveToStorage();
        renderSentences();
        showStatusMessage(`Generated ${data.count} example sentences!`, 'success');

    } catch (error) {
        showStatusMessage(error.message, 'error');
        renderSentences(); // Show existing or empty state
    }
}

// Render sentences
function renderSentences() {
    if (sentences.length === 0) {
        elements.sentencesContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📝</span>
                <p>No sentences yet</p>
                <p class="empty-hint">Upload a document and generate sentences</p>
            </div>
        `;
        return;
    }

    elements.sentencesContainer.innerHTML = sentences.map(item => `
        <div class="sentence-card">
            <div class="sentence-word">
                <span class="word-pair highlight">${escapeHtml(item.english)}</span>
                <span class="word-separator">→</span>
                <span class="word-pair highlight">${escapeHtml(item.foreign)}</span>
            </div>
            <p class="sentence-text en">${escapeHtml(item.english_sentence)}</p>
            <p class="sentence-text foreign">${escapeHtml(item.foreign_sentence)}</p>
        </div>
    `).join('');
}

// Quiz functions
async function startQuiz() {
    if (wordPairs.length < 4) return;

    showLoading(elements.quizContainer);
    elements.quizHeader.style.display = 'none';

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/mcq`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_pairs: wordPairs })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate quiz');
        }

        mcqQuestions = data.questions;
        currentQuizIndex = 0;
        quizScore = 0;
        saveToStorage();

        elements.quizHeader.style.display = 'flex';
        elements.startQuizBtn.classList.add('hidden');
        elements.resetQuizBtn.classList.remove('hidden');

        renderQuestion();
        showStatusMessage('Quiz started! Good luck!', 'info');

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
            <p class="question-text">${escapeHtml(question.question)}</p>
            <div class="quiz-options">
                ${question.options.map((option, index) => `
                    <button class="quiz-option" onclick="selectOption('${escapeHtml(option)}', '${escapeHtml(question.correct)}', this)">
                        ${escapeHtml(option)}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
}

function selectOption(selected, correct, button) {
    const options = elements.quizContainer.querySelectorAll('.quiz-option');
    options.forEach(opt => opt.disabled = true);

    if (selected === correct) {
        button.classList.add('correct');
        quizScore++;
        showStatusMessage('Correct!', 'success');
    } else {
        button.classList.add('incorrect');
        options.forEach(opt => {
            if (opt.textContent === correct) {
                opt.classList.add('correct');
            }
        });
        showStatusMessage(`Incorrect. The answer was: ${correct}`, 'error');
    }

    setTimeout(() => {
        currentQuizIndex++;
        renderQuestion();
    }, 1500);
}

function showQuizResult() {
    const percentage = Math.round((quizScore / mcqQuestions.length) * 100);
    let emoji, message;

    if (percentage === 100) {
        emoji = '🏆';
        message = 'Perfect score!';
    } else if (percentage >= 80) {
        emoji = '🌟';
        message = 'Excellent work!';
    } else if (percentage >= 60) {
        emoji = '👍';
        message = 'Good job!';
    } else if (percentage >= 40) {
        emoji = '📚';
        message = 'Keep practicing!';
    } else {
        emoji = '💪';
        message = 'Don\'t give up!';
    }

    elements.quizContainer.innerHTML = `
        <div class="quiz-result">
            <div class="result-emoji">${emoji}</div>
            <div class="result-score">${quizScore} / ${mcqQuestions.length}</div>
            <div class="result-message">${message}</div>
        </div>
    `;
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

// Helper functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(container) {
    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p class="loading-text">Loading...</p>
        </div>
    `;
}