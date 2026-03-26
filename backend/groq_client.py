"""
AI client module - uses Groq API for AI-powered content generation.
Groq provides fast inference with open-source models like Llama.
"""

import json
import re
import logging
import os
import random
import requests
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
MODEL_NAME = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
CHUNK_SIZE = 3000


class GroqClientError(Exception):
    """Custom exception for AI client errors."""
    pass


class GroqClient:
    """
    AI client using Groq API.
    Keeps the same class name so main.py needs zero changes.
    Accepts a per-request API key that overrides the env-based key.
    """

    def __init__(self, base_url: str = None, model: str = None):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = model or MODEL_NAME
        self.base_url = base_url  # kept for compatibility, not used
        logger.info(f"GroqClient initialized - model: {self.model}")

    def _resolve_key(self, api_key: Optional[str]) -> str:
        """Return per-request key if provided, else fall back to env key."""
        key = api_key if api_key else self.api_key
        if not key:
            raise GroqClientError(
                "No Groq API key provided. Please enter your API key in the app."
            )
        return key

    def _generate(self, prompt: str, api_key: Optional[str] = None) -> str:
        """Send prompt to Groq API, return text response."""
        key = self._resolve_key(api_key)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a language learning assistant. "
                        "You MUST respond with ONLY valid JSON — no explanations, "
                        "no markdown code fences, no extra text whatsoever."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            logger.info(f"Calling Groq API with model: {self.model}")
            response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=120)
            
            if response.status_code != 200:
                logger.error(f"Groq API error {response.status_code}: {response.text}")
                # Specifically handle Cloudflare 1010
                if response.status_code == 403 and "1010" in response.text:
                    raise GroqClientError("Groq API access blocked by security filter (Error 1010). Please try again or check your API key.")
                raise GroqClientError(f"Groq API error {response.status_code}: {response.text}")

            data = response.json()
            result = data["choices"][0]["message"]["content"]
            logger.info(f"Groq response length: {len(result)} chars")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error calling Groq: {str(e)}")
            raise GroqClientError(f"Network error calling Groq: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise GroqClientError(f"Unexpected error: {str(e)}")

    def _parse_json_from_response(self, response: str) -> Any:
        """Robustly extract JSON from response, handling any wrapping text."""
        # Strip markdown code fences if present
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()

        # Attempt 1: full parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: find a JSON array
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Attempt 3: find a JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Attempt 4: collect all individual JSON objects from a broken array
        objects = re.findall(r'\{[^{}]+\}', cleaned, re.DOTALL)
        if objects:
            parsed = []
            for obj in objects:
                try:
                    parsed.append(json.loads(obj))
                except json.JSONDecodeError:
                    continue
            if parsed:
                return parsed

        logger.error(f"Failed to parse JSON. Raw response: {response}")
        logger.error(f"Cleaned response: {cleaned}")
        raise GroqClientError(f"Could not parse JSON from response: {cleaned[:300]}")

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
        """Split large text into smaller chunks by line boundaries."""
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

    # ------------------------------------------------------------------ #
    #  Public API methods — each accepts an optional per-request api_key  #
    # ------------------------------------------------------------------ #

    def extract_word_pairs(self, text: str, api_key: Optional[str] = None) -> List[Dict[str, str]]:
        """Extract English-foreign word pairs from document text."""
        if len(text) > 15000:
            logger.warning(f"Input text is {len(text)} chars. Truncating to 15000 chars.")
        text = text[:15000]
        chunks = self._chunk_text(text, CHUNK_SIZE)
        logger.info(f"Processing {len(chunks)} chunk(s) of text")

        all_pairs = []
        seen = set()
        errors = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")

            prompt = (
                "Extract all English-foreign language word pairs from the text below.\n\n"
                "STRICT RULES:\n"
                "- The value of \"english\" MUST be the English word (standard a-z only, no accents)\n"
                "- The value of \"foreign\" MUST be the non-English translation\n"
                "- Return ONLY a valid JSON array of objects, nothing else\n"
                "- Each object must have exactly two keys: \"english\" and \"foreign\"\n"
                "- If no pairs are found, return an empty array: []\n\n"
                "EXAMPLE OUTPUT:\n"
                '[{"english": "apple", "foreign": "Apfel"}, {"english": "hello", "foreign": "Hallo"}]\n\n'
                f"TEXT:\n{chunk}"
            )

            try:
                response = self._generate(prompt, api_key)
                
                # Debug logging
                with open("debug_groq_response.txt", "a", encoding="utf-8") as f:
                    f.write(f"--- RAW RESPONSE ---\n{response}\n\n")

                pairs = self._parse_json_from_response(response)

                # Fallback if LLM wrapped array in a dictionary (e.g., {"pairs": [...]})
                if isinstance(pairs, dict):
                    found_list = False
                    for val in pairs.values():
                        if isinstance(val, list):
                            pairs = val
                            found_list = True
                            break
                    if not found_list:
                        # Convert dict mapping to list
                        pairs = [{"english": str(k), "foreign": str(v)} for k, v in pairs.items()]

                if isinstance(pairs, list):
                    # Normalize keys before orientation fix
                    normalized_pairs = []
                    for pair in pairs:
                        if isinstance(pair, list) and len(pair) >= 2:
                            eng, forn = str(pair[0]).strip(), str(pair[1]).strip()
                            if eng.lower() not in ["english", "word", "german", "foreign"]:
                                if eng and forn:
                                    normalized_pairs.append({"english": eng, "foreign": forn})
                                    
                        elif isinstance(pair, dict) and len(pair) >= 2:
                            pair_lower = {str(k).lower(): v for k, v in pair.items() if isinstance(k, str)}
                            eng = str(pair_lower.get("english", "")).strip()
                            forn = str(pair_lower.get("foreign", "")).strip()
                            
                            # If prompt-specified keys were ignored
                            if not forn:
                                for k, v in pair_lower.items():
                                    if k != "english":
                                        forn = str(v).strip()
                                        break
                                        
                            if not eng and len(pair_lower) == 2:
                                vals = list(pair_lower.values())
                                eng, forn = str(vals[0]).strip(), str(vals[1]).strip()
                                
                            if eng and forn:
                                normalized_pairs.append({"english": eng, "foreign": forn})

                    pairs = self._fix_pair_orientation(normalized_pairs)
                    
                    for pair in pairs:
                        english = pair.get("english", "")
                        foreign = pair.get("foreign", "")
                        key = (english.lower(), foreign.lower())
                        if key not in seen and english and foreign and english != foreign:
                            seen.add(key)
                            all_pairs.append({"english": english, "foreign": foreign})
            except GroqClientError as e:
                logger.warning(f"Chunk {i+1} failed: {e}")
                errors.append(e)
                continue

        if not all_pairs and errors:
            raise errors[0]

        logger.info(f"Total word pairs extracted: {len(all_pairs)}")
        return all_pairs

    def generate_example_sentences(
        self,
        word_pairs: List[Dict[str, str]],
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate bilingual example sentences for word pairs in batches of 10."""
        all_sentences = []
        errors = []

        for i in range(0, len(word_pairs), 10):
            batch = word_pairs[i:i + 10]
            pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in batch])

            prompt = (
                "For each word pair below, write one short example sentence in English "
                "and one in the foreign language showing the word in natural context.\n\n"
                "Return ONLY a valid JSON array. Each element must have exactly these four keys:\n"
                "\"english\", \"foreign\", \"english_sentence\", \"foreign_sentence\"\n\n"
                f"Word pairs:\n{pairs_text}"
            )

            try:
                response = self._generate(prompt, api_key)
                sentences = self._parse_json_from_response(response)

                if isinstance(sentences, dict):
                    found_list = False
                    for val in sentences.values():
                        if isinstance(val, list):
                            sentences = val
                            found_list = True
                            break
                    if not found_list:
                        sentences = [sentences]

                if isinstance(sentences, list):
                    for item in sentences:
                        if isinstance(item, dict):
                            item_lower = {str(k).lower(): v for k, v in item.items() if isinstance(k, str)}
                            if "english" in item_lower:
                                all_sentences.append({
                                    "english": str(item_lower.get("english", "")).strip(),
                                    "foreign": str(item_lower.get("foreign", "")).strip(),
                                    "english_sentence": str(item_lower.get("english_sentence", "")).strip(),
                                    "foreign_sentence": str(item_lower.get("foreign_sentence", "")).strip()
                                })
            except GroqClientError as e:
                logger.warning(f"Sentence batch {i} failed: {e}")
                errors.append(e)
                continue

        if not all_sentences and errors:
            raise errors[0]

        return all_sentences

    def generate_mcq_questions(
        self,
        word_pairs: List[Dict[str, str]],
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate MCQ questions where:
        - The LLM creates a fill-in-the-blank sentence in the foreign language
          (the foreign word is replaced with _____)
        - Python builds the answer options: 1 correct + 3 random distractors
        - Options are shuffled; the correct answer is guaranteed to be among them
        """
        pairs = word_pairs[:20]
        unique_foreign_words = list(set([p["foreign"] for p in pairs]))
        pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in pairs])

        # Ask LLM to generate fill-in-the-blank sentences
        prompt = (
            "For each word pair below, write a short, natural sentence in the FOREIGN language "
            "that uses the foreign word. Then replace the foreign word with _____.\n\n"
            "Return ONLY a valid JSON array. Each element must have exactly these keys:\n"
            "  \"english\"  — the English word\n"
            "  \"foreign\"  — the correct foreign word (the answer)\n"
            "  \"sentence\" — the foreign-language sentence with the foreign word replaced by _____\n\n"
            "EXAMPLE:\n"
            '[{"english":"apple","foreign":"Apfel","sentence":"Der _____ liegt auf dem Tisch."}]\n\n'
            f"Word pairs:\n{pairs_text}"
        )

        # Build a lookup: english_word -> {foreign, sentence}
        sentence_map: Dict[str, Dict] = {}
        try:
            response = self._generate(prompt, api_key)
            items = self._parse_json_from_response(response)
            
            if isinstance(items, dict):
                found_list = False
                for val in items.values():
                    if isinstance(val, list):
                        items = val
                        found_list = True
                        break
                if not found_list:
                    items = [items]

            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item_lower = {str(k).lower(): v for k, v in item.items() if isinstance(k, str)}
                        if "english" in item_lower and "foreign" in item_lower and "sentence" in item_lower:
                            sentence_map[str(item_lower["english"]).strip().lower()] = {
                                "foreign": str(item_lower["foreign"]).strip(),
                                "sentence": str(item_lower["sentence"]).strip()
                            }
        except GroqClientError as e:
            logger.warning(f"Sentence generation for MCQ failed: {e}")
            raise e

        # Build final MCQ list — Python controls all options (no hallucinations)
        result = []
        for pair in pairs:
            correct = pair["foreign"]
            english = pair["english"]

            # Distractors: any other foreign word from the same word list (deduplicated)
            distractors = [w for w in unique_foreign_words if w != correct]
            random.shuffle(distractors)
            wrong_options = distractors[:3]

            # Need at least 3 distractors for a 4-choice question
            if len(wrong_options) < 3:
                logger.warning(f"Skipping '{english}' — not enough distractors")
                continue

            # Build options list: correct answer + distractors, then shuffle
            options = [correct] + wrong_options
            random.shuffle(options)

            # Sanity check: correct answer must be in options
            assert correct in options, f"Correct answer '{correct}' missing from options — bug!"

            # Fetch LLM sentence or fall back to a plain question
            llm_data = sentence_map.get(english.lower(), {})
            sentence = llm_data.get("sentence", "")
            if sentence and "_____" in sentence:
                # Remove LLM chatty prefixes to keep UI clean
                import re
                clean_sentence = re.sub(r'(?i)^(fill in the blanks?|fill the blank|fill in the gaps?|fill in):\s*', '', sentence).strip()
                question_text = clean_sentence
            else:
                # Fallback if LLM didn't produce a sentence
                question_text = f"What is the foreign translation of '{english}'?"

            result.append({
                "question": question_text,
                "correct": correct,
                "options": options,
                "english": english,
                "foreign": correct
            })

        return result