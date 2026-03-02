# Flashcard App

## What We're Building
A web app where users upload documents containing English and foriegn words.
The app extracts the correct pairs using AI(see into tech stack for AI model used) and generates:
1. Flashcards (flip cards showing English on front, foreign on back)
2. Example sentences using those words
3. MCQ quizzes

## Tech Stack
- Backend: Python + FastAPI
- Frontend: Pure HTML + CSS + JavaScript (no frameworks, must look great)
- AI: Ollama (local) with mistral:latest model via HTTP API
- Storage: Browser localStorage (persists across refresh)
- File parsing: python-docx, pypdf, plain text support

## Deployment Target
- Free tier: Render.com (backend) + Netlify (frontend)
- Backend must work as a standalone FastAPI app
- No paid services, no OpenAI API keys needed

## File Structure
flashcard-app/
├── backend/
│   ├── main.py           ← FastAPI app
│   ├── parser.py         ← Document text extraction
│   ├── ollama_client.py  ← Ollama API calls
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── CLAUDE.md
└── README.md

## Rules
- Frontend stores all word pairs in localStorage (survives refresh)
- Reset button clears localStorage completely
- Web responsive design
- design should be compatible with mobile too and responsive according to screen size
- Beautiful modern UI - glassmorphism style with gradients
- All Ollama calls go through the FastAPI backend (frontend never calls Ollama directly)
- Backend runs on port 8000, frontend served separately or via FastAPI static files
- Error handling everywhere - show user-friendly messages if Ollama is down

## Key API Endpoints
POST /upload          → accepts file, returns extracted word pairs as JSON
POST /flashcards      → takes word pairs, returns formatted flashcard data
POST /sentences       → takes word pairs, returns example sentences
POST /mcq             → takes word pairs, returns MCQ questions
GET  /health          → health check for deployment

## Ollama Config
- Base URL: http://localhost:11434
- Model: mistral:latest
- If Ollama unreachable, return helpful error message

## Commands
- Run backend: uvicorn main:app --reload --port 8000
- Install deps: pip install -r requirements.txt