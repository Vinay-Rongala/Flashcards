# Language Flashcards 🃏

A modern, AI-powered language learning application built with **FastAPI** (Backend) and **Vanilla JS** (Frontend). This app allows users to upload vocabulary documents (PDF, DOCX, TXT) and automatically generates flashcards, example sentences, and interactive MCQ quizzes using the **Groq API** (Llama 3).

## ✨ Features

- **AI Extraction:** Automatically extracts English-foreign word pairs from uploaded documents.
- **Robust Parsing:** Fail-safe JSON extraction that handles varied AI response formats.
- **Interactive Flashcards:** Digital cards with a sleek glassmorphism design.
- **Example Sentences:** AI-generated bilingual sentences for better context.
- **MCQ Quizzes:** Interactive multiple-choice quizzes with intelligent distractor generation.
- **Quiz Review:** High-performance summary screen to review all answered questions.
- **Privacy First:** Your API keys are stored only in your browser's local storage.

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3 (Vanilla), JavaScript (ES6+).
- **Backend:** Python, FastAPI, Uvicorn.
- **AI Models:** Groq (Llama-3.3-70b-versatile).
- **Parsing:** python-docx, PyPDF2.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) (if running local models) or a **Groq API Key**.

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Vinay-Rongala/Flashcards.git
   cd Flashcards
   ```

2. **Setup Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   # Create a .env file and add your keys (optional for local dev if using browser UI)
   # GROQ_API_KEY=your_key_here
   uvicorn main:app --reload --port 8000
   ```

3. **Setup Frontend:**
   ```bash
   cd ../frontend
   # Use any simple static server
   python -m http.server 3000
   ```
   Open `http://localhost:3000` in your browser.

## 🌐 Deployment

### Backend (Render)
1. Create a new **Web Service** on Render.
2. Connect this repository.
3. Render will use `render.yaml` to automatically configure the service.

### Frontend (Netlify)
1. Deploy the `frontend/` folder to Netlify.
2. IMPORTANT: Update `CONFIG.API_BASE_URL` in `frontend/app.js` to point to your Render backend URL.

## 📄 License
MIT License