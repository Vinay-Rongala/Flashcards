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
        # Randomly sample up to 20 pairs to ensure variety each time
        all_pairs = list(word_pairs)
        random.shuffle(all_pairs)
        selected_pairs = all_pairs[:20]

        pairs_text = "\n".join([f"{p['english']} = {p['foreign']}" for p in selected_pairs])

        # Ask LLM to generate high-quality questions and distractors
        prompt = (
            "You are an expert language examiner creating a standardized vocabulary test (like Goethe-Institut, TELC, or CEFR exams).\n"
            "For each word pair below, fetch or construct a highly standardized, realistic test question.\n"
            "RULES FOR QUESTIONS:\n"
            "1. Create a natural, commonly used sentence from standard language testing. Replace the target word with '_____' and immediately provide its English hint in parentheses. Example: 'Ich esse einen _____ (apple).'\n"
            "2. The correct answer MUST be the exact 'foreign' word from the provided pair.\n"
            "3. Provide EXACTLY 3 WRONG distractors.\n"
            "   - Distractors must be real words in the foreign language.\n"
            "   - Distractors MUST NOT be synonyms of the correct answer.\n"
            "   - Distractors must be grammatically incorrect or logically flawed in the sentence context.\n"
            "   - Ensure there is absolutely ONLY ONE valid answer that matches both the context and the English hint.\n"
            "4. Make the sentences feel like a real, standardized language certification exam rather than random strings.\n\n"
            "Return ONLY a valid JSON array. Each element must have these exact keys:\n"
            "  \"english\"  — the English word\n"
            "  \"foreign\"  — the correct foreign word\n"
            "  \"sentence\" — the standardized test sentence with the blank and hint (e.g. '_____ (Hello), wie geht\\'s?')\n"
            "  \"distractors\" — array of exactly 3 definitively wrong foreign words\n\n"
            f"Word pairs to test:\n{pairs_text}"
        )

        result = []
        try:
            response = self._generate(prompt, api_key)
            items = self._parse_json_from_response(response)
            
            if isinstance(items, dict):
                items = items.get("questions", items.get("items", [items]))
            
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict): continue
                    
                    item_lower = {str(k).lower(): v for k, v in item.items() if isinstance(k, str)}
                    eng = str(item_lower.get("english", "")).strip()
                    correct = str(item_lower.get("foreign", "")).strip()
                    sentence = str(item_lower.get("sentence", "")).strip()
                    distractors = item_lower.get("distractors", [])
                    
                    if not eng or not correct or not sentence: continue
                    if not isinstance(distractors, list) or len(distractors) < 3:
                        # Fallback distractor logic if AI fails to provide them
                        unique_f = list(set([p["foreign"] for p in selected_pairs if p["foreign"] != correct]))
                        random.shuffle(unique_f)
                        distractors = unique_f[:3]
                    
                    if len(distractors) < 3: continue

                    # Build and shuffle options
                    options = [correct] + [str(d) for d in distractors[:3]]
                    random.shuffle(options)

                    # Clean UI sentence
                    import re
                    clean_sentence = re.sub(r'(?i)^(fill in the blanks?|fill the blank|fill in the gaps?|fill in):\s*', '', sentence).strip()

                    result.append({
                        "question": clean_sentence if "_____" in clean_sentence else f"What is the foreign translation of '{eng}'?",
                        "correct": correct,
                        "options": options,
                        "english": eng,
                        "foreign": correct
                    })
        except Exception as e:
            logger.warning(f"AI MCQ generation failed: {e}. Falling back to basic logic.")
            # Basic fallback would go here if needed, but we'll let the UI handle empty results
            raise GroqClientError(f"Failed to generate varied MCQs: {str(e)}")

        return result

        return result