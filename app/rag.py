"""
Core RAG classification pipeline: Urdu claim in -> retrieved context -> LLM
classification with cultural framing checks -> structured output.
"""

import json
import os
import re
import time

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai",
).rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3.8-flash")
LLM_FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "").strip()

# Tuned for 12-doc prototype KB: scores range 0.37-0.48 with paraphrase-multilingual-MiniLM.
# Bump to ~0.5 once KB grows to hundreds of docs and similarity spread widens.
RELEVANCE_THRESHOLD = 0.40

_supabase = None


def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


def retrieve_context(claim: str, top_k: int = 3) -> list[dict]:
    """Retrieve matching KB rows without loading a local ML model.

    Render's free instance cannot hold Torch plus the embedding model. The KB
    is small enough to fetch and rank by normalized token overlap, which keeps
    the API lightweight while preserving the verified-source workflow.
    """
    query_tokens = _content_tokens(claim)
    if not query_tokens:
        return []

    result = get_supabase().table("healthguard_kb").select(
        "id,title,category,content_urdu,source_url,is_direct_urdu_source"
    ).execute()
    ranked = []
    for document in result.data:
        document_text = " ".join(
            str(document.get(field, "")) for field in ("title", "category", "content_urdu")
        )
        document_tokens = _content_tokens(document_text)
        if not document_tokens:
            continue
        overlap = query_tokens & document_tokens
        similarity = len(overlap) / max(len(query_tokens), 1)
        if similarity:
            ranked.append({**document, "similarity": similarity})

    ranked.sort(key=lambda document: document["similarity"], reverse=True)
    return [
        document
        for document in ranked[:top_k]
        if document["similarity"] >= RELEVANCE_THRESHOLD
    ]


def _content_tokens(text: str) -> set[str]:
    """Return meaningful Urdu/Latin tokens for lightweight KB matching."""
    tokens = set(re.findall(r"[\w\u0600-\u06FF]+", text.lower(), re.UNICODE))
    stop_words = {
        "اور", "کے", "کی", "کا", "سے", "میں", "ہے", "ہیں", "کو", "یہ", "کہ",
        "ایک", "پر", "نے", "the", "and", "of", "to", "is", "are", "a", "an",
    }
    return tokens - stop_words


def call_llm(prompt: str, expect_json: bool = True) -> str:
    """Call the configured OpenAI-compatible multilingual LLM provider."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY not set in .env")

    if expect_json:
        system_content = (
            "You are a health misinformation classifier for Pakistani "
            "Lady Health Workers. Always respond with valid JSON only — "
            "no markdown fences, no explanation, no extra text."
        )
    else:
        system_content = (
            "You are a precise Urdu text converter. Respond with only the "
            "converted text — no explanation, no quotes, no extra text."
        )

    request_url = f"{LLM_BASE_URL}/chat/completions"
    request_headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    models = [LLM_MODEL]
    if LLM_FALLBACK_MODEL and LLM_FALLBACK_MODEL != LLM_MODEL:
        models.append(LLM_FALLBACK_MODEL)

    resp = None
    last_request_error = None
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(3):
            try:
                resp = requests.post(
                    request_url,
                    headers=request_headers,
                    json=payload,
                    timeout=45,
                )
                last_request_error = None
            except requests.RequestException as exc:
                last_request_error = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                continue
            if resp.ok:
                break
            if expect_json and resp.status_code in (400, 404, 422):
                # Some OpenAI-compatible providers do not implement response_format.
                # The prompt still requires JSON, and classify_claim validates it.
                payload.pop("response_format", None)
                continue
            if resp.status_code not in (429, 500, 502, 503, 504):
                break
            if attempt < 2:
                time.sleep(2 ** attempt)
        if resp.ok:
            break

    if resp is None and last_request_error is not None:
        raise last_request_error
    if not resp.ok:
        detail = resp.text[:500].replace("\n", " ")
        raise requests.HTTPError(
            f"{resp.status_code} from LLM provider: {detail}",
            response=resp,
        )
    return resp.json()["choices"][0]["message"]["content"]


def is_roman_script(text: str) -> bool:
    """True if text is predominantly Latin script (Roman Urdu/English), False if Urdu script."""
    urdu_chars = len(re.findall(r"[\u0600-\u06FF]", text))
    latin_chars = len(re.findall(r"[a-zA-Z]", text))
    return latin_chars > urdu_chars


NORMALIZATION_PROMPT_TEMPLATE = """درج ذیل متن رومن اردو (لاطینی رسم الخط) یا انگریزی میں لکھا گیا صحت سے متعلق دعویٰ ہے۔ اسے معیاری اردو رسم الخط میں تبدیل کریں۔

اہم: انگریزی طبی الفاظ کے لیے اردو میں رائج معیاری الفاظ استعمال کریں، آواز کے مطابق نہیں، اور اصل متن کا مطلب بالکل برقرار رکھیں۔ مثال کے طور پر:
- "polio vaccine se bachay banjh ho jate hain" ← "پولیو ویکسین سے بچے بانجھ ہو جاتے ہیں"
- "ulama ne is se mana kiya hai" ← "علما نے اس سے منع کیا ہے"
- "yeh dawa mehfooz hai" ← "یہ دوا محفوظ ہے"
- "drops" کے لیے "قطرے"، "vaccine" کے لیے "ویکسین"، "medicine" کے لیے "دوا"

اگر متن پہلے سے اردو رسم الخط میں ہے تو اسے بغیر تبدیلی کے واپس کریں۔ صرف تبدیل شدہ اردو متن واپس کریں، کوئی اضافی وضاحت نہیں۔

متن: {text}
"""


def normalize_claim(claim: str) -> str:
    """Transliterate Roman Urdu / English health claims into Urdu script before embedding."""
    prompt = NORMALIZATION_PROMPT_TEMPLATE.format(text=claim)
    try:
        normalized = call_llm(prompt, expect_json=False).strip()
    except requests.RequestException:
        normalized = claim
    return normalized or claim


def to_urdu_script(text: str) -> str:
    """Convert Roman Urdu text to Urdu script — used to ensure TTS always gets proper Urdu script input."""
    prompt = (
        "درج ذیل متن کو اردو رسم الخط میں تبدیل کریں۔ "
        "صرف تبدیل شدہ متن واپس کریں، کوئی وضاحت نہیں:\n\n" + text
    )
    return call_llm(prompt, expect_json=False).strip()


CLASSIFICATION_PROMPT_TEMPLATE = """آپ ایک صحت سے متعلق غلط معلومات کی شناخت کرنے والا معاون ہیں، جو پاکستان کے لیڈی ہیلتھ ورکرز کی مدد کے لیے بنایا گیا ہے۔

صارف کا دعویٰ:
{claim}

تصدیق شدہ ذرائع سے حاصل کردہ متعلقہ معلومات:
{context}

اپنے تجزیے میں خاص طور پر ان تین ثقافتی نمونوں کو دیکھیں:
1. مذہبی رہنمائی کے دعوے (جیسے "علماء کہتے ہیں...", حلال/حرام سے متعلق دعوے)
2. روایتی ٹوٹکوں کو طبی طور پر ثابت شدہ ظاہر کرنا
3. اینٹی ویکسین بیانیے (خاص طور پر پولیو کے قطرے، بانجھ پن کے دعوے)

اہم: confidence_score میں حقیقی غیر یقینییت کو ظاہر کریں — واضح طور پر غلط دعووں کے لیے 90-97 استعمال کریں، کبھی بھی بالکل 100 نہیں، کیونکہ ہمیشہ ایسے کنارے کے معاملات ہو سکتے ہیں جو دیکھے نہ گئے ہوں۔

{script_instruction}

اوپر دی گئی معلومات کی بنیاد پر، دعوے کا تجزیہ کریں اور نیچے دیے گئے JSON فارمیٹ میں جواب دیں،
کوئی اضافی متن شامل نہ کریں:

{{
  "category": "<ایک مختصر زمرہ، مثلاً: پولیو ویکسین - بانجھ پن کا دعویٰ>",
  "confidence_score": <0-100 کے درمیان نمبر>,
  "cultural_framing_detected": ["<لاگو ہونے والے نمونے، خالی فہرست اگر کوئی نہیں>"],
  "counter_message_urdu": "<ایک مختصر، سادہ اردو میں جوابی پیغام جو صارف فوری طور پر آگے بھیج سکے>",
  "knowledge_base_match": true
}}
"""

NO_MATCH_PROMPT_TEMPLATE = """آپ ایک صحت سے متعلق غلط معلومات کی شناخت کرنے والا معاون ہیں، جو پاکستان کے لیڈی ہیلتھ ورکرز کی مدد کے لیے بنایا گیا ہے۔

صارف کا دعویٰ:
{claim}

نوٹ: اس دعوے کے لیے ہمارے تصدیق شدہ علم کی بنیاد میں کوئی متعلقہ ماخذ نہیں ملا۔ اپنا تجزیہ عام طبی احتیاط اور عمومی علم کی بنیاد پر کریں۔

اپنے تجزیے میں خاص طور پر ان تین ثقافتی نمونوں کو دیکھیں:
1. مذہبی رہنمائی کے دعوے (جیسے "علماء کہتے ہیں...", حلال/حرام سے متعلق دعوے)
2. روایتی ٹوٹکوں کو طبی طور پر ثابت شدہ ظاہر کرنا
3. اینٹی ویکسین بیانیے (خاص طور پر پولیو کے قطرے، بانجھ پن کے دعوے)

اہم: confidence_score میں حقیقی غیر یقینییت کو ظاہر کریں — واضح طور پر غلط دعووں کے لیے 90-97 استعمال کریں۔ چونکہ ہمارے پاس تصدیق شدہ ماخذ نہیں ہے، confidence_score کو 70 سے زیادہ نہ رکھیں۔

{script_instruction}

دعوے کا تجزیہ کریں اور نیچے دیے گئے JSON فارمیٹ میں جواب دیں، کوئی اضافی متن شامل نہ کریں:

{{
  "category": "<ایک مختصر زمرہ>",
  "confidence_score": <0-70 کے درمیان نمبر>,
  "cultural_framing_detected": ["<لاگو ہونے والے نمونے، خالی فہرست اگر کوئی نہیں>"],
  "counter_message_urdu": "<ایک مختصر، سادہ اردو میں جوابی پیغام جو صارف فوری طور پر آگے بھیج سکے>",
  "knowledge_base_match": false
}}
"""


def classify_claim(raw_claim: str) -> dict:
    """Full pipeline: normalize script, retrieve context, classify with LLM, return structured result."""
    input_is_roman = is_roman_script(raw_claim)
    retrieved = []
    top_similarity = 0.0
    if input_is_roman:
        # Retrieval runs on Urdu script: multilingual embeddings score Roman and Urdu
        # versions of the same sentence very differently. Transliteration quality also
        # varies between runs (verb choice like منع/منا/انکار embeds differently), so
        # normalize up to 3 times and keep the best-scoring retrieval — one weak
        # translation can no longer lose an otherwise-clear KB match.
        seen_variants = set()
        for _ in range(3):
            variant = normalize_claim(raw_claim)
            if variant in seen_variants:
                continue
            seen_variants.add(variant)
            docs = retrieve_context(variant, top_k=3)
            sim = float(docs[0]["similarity"]) if docs else 0.0
            if sim > top_similarity:
                retrieved, top_similarity = docs, sim
            if top_similarity >= RELEVANCE_THRESHOLD + 0.05:
                break  # comfortable margin — no need for more variants
        # Raw-claim retrieval as a final fallback
        if top_similarity < RELEVANCE_THRESHOLD:
            docs_raw = retrieve_context(raw_claim, top_k=3)
            sim_raw = float(docs_raw[0]["similarity"]) if docs_raw else 0.0
            if sim_raw > top_similarity:
                retrieved, top_similarity = docs_raw, sim_raw
    else:
        retrieved = retrieve_context(raw_claim, top_k=3)
        top_similarity = float(retrieved[0]["similarity"]) if retrieved else 0.0

    # Check relevance: use top similarity score to decide if KB has useful context
    kb_match = top_similarity >= RELEVANCE_THRESHOLD

    # Match the counter-message script to the script the user actually wrote in.
    # Scoped to counter_message_urdu ONLY — category and framing labels stay Urdu always.
    script_instruction = (
        "اہم: صرف 'counter_message_urdu' فیلڈ رومن اردو (لاطینی رسم الخط) میں لکھیں، "
        "کیونکہ صارف نے اپنا سوال رومن اردو میں پوچھا ہے۔ مثال کے طور پر: 'yeh dawa mehfooz hai'۔ "
        "باقی تمام فیلڈز — 'category' اور 'cultural_framing_detected' — ہمیشہ اردو رسم الخط میں لکھیں۔"
        if input_is_roman
        else "تمام فیلڈز — 'category'، 'cultural_framing_detected' اور 'counter_message_urdu' — اردو رسم الخط میں لکھیں۔"
    )

    if kb_match:
        context_text = "\n\n".join(
            f"- {doc['content_urdu']} (\u0645\u0627\u062e\u0630: {doc['source_url']})" for doc in retrieved
        )
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            claim=raw_claim, context=context_text, script_instruction=script_instruction
        )
    else:
        prompt = NO_MATCH_PROMPT_TEMPLATE.format(
            claim=raw_claim, script_instruction=script_instruction
        )

    llm_response_text = call_llm(prompt)

    try:
        result = json.loads(llm_response_text)
    except json.JSONDecodeError:
        cleaned = llm_response_text.strip().strip("```json").strip("```").strip()
        result = json.loads(cleaned)

    # Force the KB match flag to match our threshold check
    result["knowledge_base_match"] = kb_match

    # Only attach sources if we actually used the KB
    if kb_match:
        result["retrieved_sources"] = [
            {"title": doc["title"], "source_url": doc["source_url"]} for doc in retrieved
        ]
    else:
        result["retrieved_sources"] = []

    return result
