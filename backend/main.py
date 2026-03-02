"""
FastAPI backend for the Flashcard App.
Handles file uploads, document parsing, and AI-powered content generation.
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

from parser import DocumentParser
from ollama_client import OllamaClient, OllamaClientError
from dotenv import load_dotenv
load_dotenv()

# ============================================
# Configuration
# ============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Initialize FastAPI app
app = FastAPI(
    title="Flashcard App API",
    description="API for document processing and AI-generated flashcards, sentences, and MCQs",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Ollama client with environment variables
ollama_client = OllamaClient()


# Pydantic models for request/response
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


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model: str


# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Flashcard App API",
        "version": "1.0.0",
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
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "groq_api_key_set": bool(os.getenv("GROQ_API_KEY", ""))
    }


@app.post("/upload", tags=["Upload"])
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document to extract English-foreign word pairs.

    Supports: PDF, DOCX, TXT files

    Returns:
        JSON response with extracted word pairs

    Raises:
        HTTPException: If file format is unsupported or parsing fails
    """
    try:
        # Read file content
        file_content = await file.read()

        # Parse the document
        parser = DocumentParser(file_content, file.filename)
        text = parser.extract_text()

        # Extract word pairs using Ollama
        word_pairs = ollama_client.extract_word_pairs(text)

        if not word_pairs:
            raise HTTPException(
                status_code=400,
                detail="No word pairs could be extracted from the document. "
                       "Please ensure the document contains clear English-foreign word pairs."
            )

        return {
            "success": True,
            "filename": file.filename,
            "word_pairs": word_pairs,
            "count": len(word_pairs)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OllamaClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.post("/flashcards", response_model=FlashcardResponse, tags=["Flashcards"])
async def create_flashcards(request: FlashcardRequest):
    """
    Create formatted flashcard data from word pairs.

    Args:
        request: FlashcardRequest containing word pairs

    Returns:
        Formatted flashcard data
    """
    try:
        if not request.word_pairs:
            raise HTTPException(
                status_code=400,
                detail="No word pairs provided"
            )

        # Format flashcards
        flashcards = [
            {
                "id": i,
                "front": pair["english"],
                "back": pair["foreign"]
            }
            for i, pair in enumerate(request.word_pairs)
        ]

        return {
            "flashcards": flashcards,
            "count": len(flashcards)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create flashcards: {str(e)}"
        )


@app.post("/sentences", response_model=SentenceResponse, tags=["Sentences"])
async def generate_sentences(request: FlashcardRequest):
    """
    Generate example sentences for each word pair.

    Args:
        request: FlashcardRequest containing word pairs

    Returns:
        Sentences with examples in both languages
    """
    try:
        if not request.word_pairs:
            raise HTTPException(
                status_code=400,
                detail="No word pairs provided"
            )

        # Generate sentences using Ollama
        sentences = ollama_client.generate_example_sentences(request.word_pairs)

        return {
            "sentences": sentences,
            "count": len(sentences)
        }

    except OllamaClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate sentences: {str(e)}"
        )


@app.post("/mcq", response_model=MCQResponse, tags=["Quiz"])
async def generate_mcq(request: MCQRequest):
    """
    Generate multiple choice questions for word pairs.

    Args:
        request: MCQRequest containing word pairs

    Returns:
        MCQ questions with options and correct answers
    """
    try:
        if not request.word_pairs:
            raise HTTPException(
                status_code=400,
                detail="No word pairs provided"
            )

        if len(request.word_pairs) < 4:
            raise HTTPException(
                status_code=400,
                detail="At least 4 word pairs are required to generate MCQs"
            )

        # Generate MCQ questions using Ollama
        questions = ollama_client.generate_mcq_questions(request.word_pairs)

        return {
            "questions": questions,
            "count": len(questions)
        }

    except OllamaClientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate MCQ questions: {str(e)}"
        )


# Error handlers
@app.exception_handler(OllamaClientError)
async def ollama_exception_handler(request, exc):
    """Handle AI client errors."""
    return HTTPException(
        status_code=503,
        detail={
            "error": "AI Service Unavailable",
            "message": str(exc),
            "suggestion": "Please ensure your GROQ_API_KEY is set in the .env file"
        }
    )


# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )