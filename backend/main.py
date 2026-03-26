"""
FastAPI backend for the Flashcard App.
Handles file uploads, document parsing, and AI-powered content generation.
The Groq API key is supplied per-request via the X-Groq-Api-Key HTTP header.
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

from parser import DocumentParser
from groq_client import GroqClient, GroqClientError
from dotenv import load_dotenv

# Force loading latest .env (user just added OPENAI_API_KEY)
load_dotenv(override=True)

# Initialize FastAPI app
app = FastAPI(
    title="Flashcard App API",
    description="API for document processing and AI-generated flashcards, sentences, and MCQs",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize client (env key used only as fallback if header is absent)
groq_client = GroqClient()


# ============================================================
# Helpers
# ============================================================

def get_api_key(request: Request) -> str:
    """
    Resolve the Groq API key.
    Priority: X-Groq-Api-Key header > GROQ_API_KEY env var.
    Raises 401 if neither is set.
    """
    key = request.headers.get("X-Groq-Api-Key", "").strip()
    if not key:
        key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=401,
            detail="No Groq API key provided. Send it in the X-Groq-Api-Key header."
        )
    return key


# ============================================================
# Pydantic models
# ============================================================

class FlashcardRequest(BaseModel):
    word_pairs: List[Dict[str, str]]


class FlashcardResponse(BaseModel):
    flashcards: List[Dict[str, str]]
    count: int


class SentenceResponse(BaseModel):
    sentences: List[Dict[str, Any]]
    count: int


class MCQRequest(BaseModel):
    word_pairs: List[Dict[str, str]]


class MCQResponse(BaseModel):
    questions: List[Dict[str, Any]]
    count: int


# ============================================================
# Endpoints
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Flashcard App API",
        "version": "1.0.0",
        "auth": "Pass your Groq API key in the X-Groq-Api-Key header",
        "endpoints": {
            "upload": "POST /upload",
            "flashcards": "POST /flashcards",
            "sentences": "POST /sentences",
            "mcq": "POST /mcq",
            "health": "GET /health"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "ai_provider": "Groq",
        "model": os.getenv("GROQ_MODEL", "llama3-70b-8192"),
        "note": "Pass your Groq API key in the X-Groq-Api-Key request header"
    }


@app.post("/upload", tags=["Upload"])
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Upload and process a document to extract English-foreign word pairs.
    Supports: PDF, DOCX, TXT
    Requires: X-Groq-Api-Key header
    """
    api_key = get_api_key(request)

    try:
        file_content = await file.read()

        # Parse document to raw text
        parser = DocumentParser(file_content, file.filename)
        text = parser.extract_text()

        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the document. Please check the file."
            )

        # Extract word pairs using Groq
        word_pairs = groq_client.extract_word_pairs(text, api_key=api_key)

        if not word_pairs:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No word pairs could be extracted from the document. "
                    "Please ensure the document contains clear English-foreign word pairs."
                )
            )

        return {
            "success": True,
            "filename": file.filename,
            "word_pairs": word_pairs,
            "count": len(word_pairs)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GroqClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.post("/flashcards", response_model=FlashcardResponse, tags=["Flashcards"])
async def create_flashcards(request: Request, body: FlashcardRequest):
    """
    Format word pairs as flashcard objects.
    No AI needed — pure Python transformation.
    """
    # API key not strictly needed here (no AI call), but we still validate it
    # so a stale/missing key surfaces early.
    get_api_key(request)

    try:
        if not body.word_pairs:
            raise HTTPException(status_code=400, detail="No word pairs provided")

        flashcards = [
            {"id": str(i), "front": pair["english"], "back": pair["foreign"]}
            for i, pair in enumerate(body.word_pairs)
        ]

        return {"flashcards": flashcards, "count": len(flashcards)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create flashcards: {str(e)}")


@app.post("/sentences", response_model=SentenceResponse, tags=["Sentences"])
async def generate_sentences(request: Request, body: FlashcardRequest):
    """
    Generate bilingual example sentences for each word pair.
    Requires: X-Groq-Api-Key header
    """
    api_key = get_api_key(request)

    try:
        if not body.word_pairs:
            raise HTTPException(status_code=400, detail="No word pairs provided")

        sentences = groq_client.generate_example_sentences(body.word_pairs, api_key=api_key)

        return {"sentences": sentences, "count": len(sentences)}

    except GroqClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate sentences: {str(e)}")


@app.post("/mcq", response_model=MCQResponse, tags=["Quiz"])
async def generate_mcq(request: Request, body: MCQRequest):
    """
    Generate fill-in-the-blank MCQ questions.
    LLM creates context sentences; Python builds shuffled options.
    Requires: X-Groq-Api-Key header and at least 4 word pairs.
    """
    api_key = get_api_key(request)

    try:
        if not body.word_pairs:
            raise HTTPException(status_code=400, detail="No word pairs provided")

        if len(body.word_pairs) < 4:
            raise HTTPException(
                status_code=400,
                detail="At least 4 word pairs are required to generate MCQs"
            )

        questions = groq_client.generate_mcq_questions(body.word_pairs, api_key=api_key)

        return {"questions": questions, "count": len(questions)}

    except GroqClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate MCQ questions: {str(e)}")


# ============================================================
# Run
# ============================================================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)