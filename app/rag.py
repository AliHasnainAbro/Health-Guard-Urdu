"""
Core RAG classification pipeline: Urdu claim in -> retrieved context -> LLM
classification with cultural framing checks -> structured output.
"""

import json
import os
import re

import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"

# Tuned for 12-doc prototype KB: scores range 0.37-0.48 with paraphrase-multilingual-MiniLM.
# Bump to ~0.5 once KB grows to hundreds of docs and similarity spread widens.
RELEVANCE_THRESHOLD = 0.40

_model = None
_supabase = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


def retrieve_context(claim: str, top_k: int = 3) -> list[dict]:
    """Embed the claim and retrieve similar KB documents.

    Only documents clearing RELEVANCE_THRESHOLD are returned — a strong overall
    match should not drag in filler docs that merely happen to be third-closest.
    """
    embedding = get_model().encode(claim).tolist()
    result = get_supabase().rpc(
        "match_healthguard_kb",
        {"query_embedding": embedding, "match_count": top_k},
    ).execute()
    return [d for d in result.data if float(d["similarity"]) >= RELEVANCE_THRESHOLD]


def call_llm(prompt: str, expect_json: bool = True) -> str:
    """Call Qwen via Alibaba Cloud DashScope (OpenAI-compatible endpoint)."""
    if not QWEN_API_KEY:
        raise RuntimeError("QWEN_API_KEY not set in .env")

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

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    if expect_json:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(
        f"{QWEN_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
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
    normalized = call_llm(prompt, expect_json=False).strip()
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
