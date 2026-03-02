"""
Ollama client module for AI model interactions.
Handles HTTP API calls to local Ollama server.
"""

import json
import re
import requests
import logging
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "mistral:latest"
CHUNK_SIZE = 3000  # characters per chunk sent to Ollama


class OllamaClientError(Exception):
    pass


class OllamaClient:

    def __init__(self, base_url: str = "http://localhost:11434", model: str = MODEL_NAME):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_url = f"{self.base_url}/api/generate"

    def _check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _generate(self, prompt: str) -> str:
        """Send prompt to Ollama, return raw text response."""
        if not self._check_connection():
            raise OllamaClientError(
                f"Ollama is not running. Please start it with: ollama serve"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
            # NOTE: No "format":"json" — Mistral handles it poorly
        }

        try:
            logger.info(f"Calling Ollama model: {self.model}")
            response = requests.post(self.api_url, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            result = data.get("response", "")
            logger.info(f"Ollama response length: {len(result)} chars")
            logger.debug(f"Ollama raw response: {result[:500]}")
            return result
        except requests.Timeout:
            raise OllamaClientError("Ollama timed out. Try a smaller file or simpler prompt.")
        except requests.RequestException as e:
            raise OllamaClientError(f"Ollama request failed: {str(e)}")

    def _parse_json_from_response(self, response: str) -> Any:
        """
        Robustly extract JSON from Ollama response.
        Handles markdown fences, extra text, and partial responses.
        """
        # Remove markdown code fences
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try finding JSON array in the response
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from response: {cleaned[:300]}")
        raise OllamaClientError(f"Could not parse JSON from AI response. Raw: {cleaned[:200]}")

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

    def extract_word_pairs(self, text: str) -> List[Dict[str, str]]:
        """
        Extract English-foreign word pairs from text.
        Splits large text into chunks to avoid overwhelming the model.
        """
        # Limit total text size
        text = text[:15000]

        chunks = self._chunk_text(text, CHUNK_SIZE)
        logger.info(f"Processing {len(chunks)} chunk(s) of text")

        all_pairs = []
        seen = set()

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")

            prompt = f"""Look at this text and extract all English-foreign language word pairs.
Return ONLY a JSON array. Each item must have "english" and "foreign" keys.
No explanations. No extra text. Just the JSON array.

If you find no pairs, return an empty array: []

Text:
{chunk}

JSON array:"""

            try:
                response = self._generate(prompt)
                pairs = self._parse_json_from_response(response)

                if isinstance(pairs, list):
                    for pair in pairs:
                        if isinstance(pair, dict) and "english" in pair and "foreign" in pair:
                            english = str(pair["english"]).strip().lower()
                            foreign = str(pair["foreign"]).strip()
                            key = (english, foreign.lower())
                            if key not in seen and english and foreign:
                                seen.add(key)
                                all_pairs.append({
                                    "english": str(pair["english"]).strip(),
                                    "foreign": foreign
                                })
            except OllamaClientError as e:
                logger.warning(f"Chunk {i+1} failed: {e}")
                continue

        logger.info(f"Total word pairs extracted: {len(all_pairs)}")
        return all_pairs

    def generate_example_sentences(self, word_pairs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate example sentences for word pairs. Process in batches of 10."""
        all_sentences = []

        # Process in batches of 10 to avoid token limits
        batch_size = 10
        for i in range(0, len(word_pairs), batch_size):
            batch = word_pairs[i:i + batch_size]
            pairs_text = "\n".join([
                f"{p['english']} = {p['foreign']}"
                for p in batch
            ])

            prompt = f"""For each word pair below, write one short example sentence in English and one in the foreign language.
Return ONLY a JSON array. Each item must have: "english", "foreign", "english_sentence", "foreign_sentence".
No explanations. Just the JSON array.

Word pairs:
{pairs_text}

JSON array:"""

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
        """Generate MCQ questions - Mistral writes questions, Python builds options."""
        import random

        pairs = word_pairs[:20]
        all_foreign_words = [p["foreign"] for p in pairs]

        # Ask Mistral ONLY to write creative question text, nothing else
        pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in pairs])

        prompt = f"""You are a quiz generator. Write one English question for each word pair below.
        The question MUST be in English only.
        The question asks the user to translate the English word/phrase into the foreign language.

        Format: "How do you say '[english]' in the foreign language?"
        OR: "Translate '[english]' into the foreign language."
        OR: "What is the translation of '[english]'?"

        Return ONLY a JSON array with "english" and "question" keys.
        The "question" value must always be in English.
        No explanations. Just JSON.

        Word pairs:
        {pairs_text}

        JSON array:"""

        # Get question texts from Mistral
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

            # Use Mistral's question if available, fallback to default
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