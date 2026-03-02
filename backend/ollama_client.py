"""
AI client module - uses Groq API for AI-powered content generation.
Groq provides fast inference with open-source models like Llama.
"""

import json
import re
import logging
import os
import random
from typing import Dict, List, Any
from urllib import request, error as urllib_error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CHUNK_SIZE = 3000


class OllamaClientError(Exception):
    """Custom exception for AI client errors."""
    pass


class OllamaClient:
    """
    AI client using Groq API.
    Keeps the same class name so main.py needs zero changes.
    """

    def __init__(self, base_url: str = None, model: str = None):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = model or MODEL_NAME
        self.base_url = base_url  # kept for compatibility, not used
        logger.info(f"GroqClient initialized - API Key prefix: {self.api_key[:10]}... if set")
        logger.info(f"Using model: {self.model}")

    def _check_connection(self) -> bool:
        """Check if Groq API key is set."""
        return bool(self.api_key)

    def _generate(self, prompt: str) -> str:
        """Send prompt to Groq API, return text response."""
        if not self.api_key:
            raise OllamaClientError(
                "GROQ_API_KEY environment variable is not set. "
                "Get a free key at console.groq.com"
            )

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful language learning assistant. Always respond with valid JSON only, no extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }).encode("utf-8")

        req = request.Request(
            GROQ_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            method="POST"
        )

        try:
            logger.info(f"Calling Groq API with model: {self.model}")
            logger.info(f"API Key: {self.api_key[:10]}... (length: {len(self.api_key)})")
            with request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = data["choices"][0]["message"]["content"]
                logger.info(f"Groq response length: {len(result)} chars")
                return result
        except urllib_error.HTTPError as e:
            body = e.read().decode("utf-8")
            logger.error(f"Groq API error {e.code}: {body}")
            raise OllamaClientError(f"Groq API error {e.code}: {body}")
        except urllib_error.URLError as e:
            raise OllamaClientError(f"Network error calling Groq: {str(e)}")
        except Exception as e:
            raise OllamaClientError(f"Unexpected error: {str(e)}")

    def _parse_json_from_response(self, response: str) -> Any:
        """Robustly extract JSON from response."""
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise OllamaClientError(f"Could not parse JSON from response: {cleaned[:200]}")

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
        """Split large text into smaller chunks."""
        lines = text.split('\n')
        chunks = []
        current = []
        current_len = 0

        for line in lines:
            if current_len + len(line) > chunk_size and current:
                chunks.append('\n'.join(current))
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += len(line)

        if current:
            chunks.append('\n'.join(current))

        return chunks

    def _is_english(self, word: str) -> bool:
        """Check if a word is likely English (no special foreign chars)."""
        non_english_chars = set(
            'äöüßàáâãåæçèéêëìíîïðñòóôõøùúûýþÿőű'
            'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        )
        return not any(c in non_english_chars for c in word)

    def _fix_pair_orientation(self, pairs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ensure english key always has the English word."""
        fixed = []
        for pair in pairs:
            english = pair.get("english", "")
            foreign = pair.get("foreign", "")
            if not self._is_english(english) and self._is_english(foreign):
                logger.info(f"Auto-correcting swapped pair: '{english}' <-> '{foreign}'")
                fixed.append({"english": foreign, "foreign": english})
            else:
                fixed.append({"english": english, "foreign": foreign})
        return fixed

    def extract_word_pairs(self, text: str) -> List[Dict[str, str]]:
        """Extract English-foreign word pairs from text."""
        if len(text) > 15000:
            logger.warning(f"Input text is {len(text)} chars. Truncating to 15000 chars.")
        text = text[:15000]
        chunks = self._chunk_text(text, CHUNK_SIZE)
        logger.info(f"Processing {len(chunks)} chunk(s) of text")

        all_pairs = []
        seen = set()

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")

            prompt = f"""Extract all English-foreign language word pairs from this text.

RULES:
- "english" key MUST contain the English word (only standard a-z letters)
- "foreign" key MUST contain the non-English translation
- Return ONLY a valid JSON array
- If no pairs found, return: []

Example output: [{{"english": "apple", "foreign": "Apfel"}}, {{"english": "hello", "foreign": "Hallo"}}]

Text:
{chunk}"""

            try:
                response = self._generate(prompt)
                pairs = self._parse_json_from_response(response)

                if isinstance(pairs, list):
                    pairs = self._fix_pair_orientation(pairs)
                    for pair in pairs:
                        if isinstance(pair, dict) and "english" in pair and "foreign" in pair:
                            english = str(pair["english"]).strip()
                            foreign = str(pair["foreign"]).strip()
                            key = (english.lower(), foreign.lower())
                            if key not in seen and english and foreign:
                                seen.add(key)
                                all_pairs.append({"english": english, "foreign": foreign})
            except OllamaClientError as e:
                logger.warning(f"Chunk {i+1} failed: {e}")
                continue

        logger.info(f"Total word pairs extracted: {len(all_pairs)}")
        return all_pairs

    def generate_example_sentences(self, word_pairs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate example sentences for word pairs in batches of 10."""
        all_sentences = []

        for i in range(0, len(word_pairs), 10):
            batch = word_pairs[i:i + 10]
            pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in batch])

            prompt = f"""For each word pair, write one short example sentence in English and one in the foreign language.

Return ONLY a valid JSON array. Each item must have exactly these keys:
"english", "foreign", "english_sentence", "foreign_sentence"

Word pairs:
{pairs_text}"""

            try:
                response = self._generate(prompt)
                sentences = self._parse_json_from_response(response)

                if isinstance(sentences, list):
                    for item in sentences:
                        if isinstance(item, dict) and "english" in item:
                            all_sentences.append({
                                "english": str(item.get("english", "")).strip(),
                                "foreign": str(item.get("foreign", "")).strip(),
                                "english_sentence": str(item.get("english_sentence", "")).strip(),
                                "foreign_sentence": str(item.get("foreign_sentence", "")).strip()
                            })
            except OllamaClientError as e:
                logger.warning(f"Sentence batch {i} failed: {e}")
                continue

        return all_sentences

    def generate_mcq_questions(self, word_pairs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate MCQ - Groq writes questions, Python builds options."""
        pairs = word_pairs[:20]
        all_foreign_words = [p["foreign"] for p in pairs]
        pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in pairs])

        prompt = f"""Write one quiz question in English for each word pair below.
The question should ask the user to identify the foreign translation.

Use varied formats:
- "How do you say '[english]' in the foreign language?"
- "Translate '[english]' into the foreign language."
- "What is the translation of '[english]'?"

Return ONLY a valid JSON array with exactly "english" and "question" keys.

Word pairs:
{pairs_text}"""

        question_map = {}
        try:
            response = self._generate(prompt)
            questions = self._parse_json_from_response(response)
            if isinstance(questions, list):
                for q in questions:
                    if isinstance(q, dict) and "english" in q and "question" in q:
                        question_map[q["english"].strip().lower()] = q["question"].strip()
        except OllamaClientError as e:
            logger.warning(f"Question generation failed, using defaults: {e}")

        # Python builds options — guaranteed correct, no hallucinations
        result = []
        for pair in pairs:
            correct = pair["foreign"]
            english = pair["english"]

            distractors = [w for w in all_foreign_words if w != correct]
            random.shuffle(distractors)
            wrong_options = distractors[:3]

            if len(wrong_options) < 3:
                continue

            options = [correct] + wrong_options
            random.shuffle(options)

            question_text = question_map.get(
                english.lower(),
                f"What is the foreign translation of '{english}'?"
            )

            result.append({
                "question": question_text,
                "correct": correct,
                "options": options,
                "english": english,
                "foreign": correct
            })

        return result