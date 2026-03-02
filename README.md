# Language Flashcards App

A web app that turns vocabulary documents into an interactive language learning experience. Upload a document, and the app automatically extracts English-foreign word pairs and gives you three ways to study them.

---

## Features

- 📄 **Multi-File Upload** — Upload multiple PDF, DOCX, or TXT files at once
- 🃏 **Flashcards** — Click-to-flip cards showing English on front, translation on back
- 📝 **Example Sentences** — AI-generated sentences showing each word in context
- ❓ **MCQ Quiz** — Multiple choice questions built from your uploaded words
- 💾 **Persistent Storage** — Words saved in browser localStorage, survive page refresh
- 🔄 **Merge Uploads** — New uploads add to existing words, nothing gets overwritten
- 🗑️ **Reset** — One button clears all stored data
- 📱 **Responsive** — Works on desktop and mobile

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| AI | Ollama (`mistral:latest`) |
| File Parsing | pypdf, python-docx |
| Storage | Browser localStorage |
| Deployment | Render.com (backend), Netlify (frontend) |

---

## Project Structure

```
flashcard-app/
├── backend/
│   ├── main.py               # FastAPI app and API endpoints
│   ├── parser.py             # Text extraction from PDF, DOCX, TXT
│   ├── ollama_client.py      # Ollama API integration
│   └── requirements.txt
├── frontend/
│   ├── index.html            # App UI
│   ├── style.css             # Glassmorphism styling
│   └── app.js                # Frontend logic and localStorage
├── render.yaml               # Render.com deployment config
├── netlify.toml              # Netlify deployment config
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check and Ollama status |
| POST | `/upload` | Upload files and extract word pairs |
| POST | `/flashcards` | Format word pairs as flashcards |
| POST | `/sentences` | Generate example sentences |
| POST | `/mcq` | Generate MCQ questions |

---

## Local Setup

**Prerequisites:** Python 3.8–3.12, Ollama installed

```bash
# 1. Pull the AI model
ollama pull mistral:latest

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Run the backend
uvicorn main:app --reload --port 8000

# 4. Serve the frontend (new terminal)
cd frontend
python -m http.server 3000
```

Open `http://localhost:3000` in your browser.

---

## Deployment

**Backend → Render.com**
- Build command: `cd backend && pip install -r requirements.txt`
- Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

**Frontend → Netlify**
- Update `API_BASE_URL` in `frontend/app.js` to your Render backend URL
- Drag and drop the `frontend/` folder to Netlify

---

## Usage

1. Go to the **Upload** tab and select one or more vocabulary documents
2. Switch to **Flashcards** to review words by flipping cards
3. Go to **Sentences** to see each word used in a real sentence
4. Open **MCQ Quiz** to test yourself and track your score
5. Hit **Reset All Data** to start fresh

---

## License

MIT License