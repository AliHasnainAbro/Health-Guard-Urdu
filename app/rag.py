"""
Core RAG classification pipeline: Urdu claim in -> retrieved context -> LLM
classification with cultural framing checks -> structured output.
"""

import json
import os

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
    """Embed the claim and retrieve the top_k most similar KB documents."""
    embedding = get_model().encode(claim).tolist()
    result = get_supabase().rpc(
        "match_healthguard_kb",
        {"query_embedding": embedding, "match_count": top_k},
    ).execute()
    return result.data


def call_llm(prompt: str) -> str:
    """Call Qwen via Alibaba Cloud DashScope (OpenAI-compatible endpoint)."""
    if not QWEN_API_KEY:
        raise RuntimeError("QWEN_API_KEY not set in .env")

    resp = requests.post(
        f"{QWEN_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": QWEN_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a health misinformation classifier for Pakistani "
                        "Lady Health Workers. Always respond with valid JSON only — "
                        "no markdown fences, no explanation, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


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

دعوے کا تجزیہ کریں اور نیچے دیے گئے JSON فارمیٹ میں جواب دیں، کوئی اضافی متن شامل نہ کریں:

{{
  "category": "<ایک مختصر زمرہ>",
  "confidence_score": <0-70 کے درمیان نمبر>,
  "cultural_framing_detected": ["<لاگو ہونے والے نمونے، خالی فہرست اگر کوئی نہیں>"],
  "counter_message_urdu": "<ایک مختصر، سادہ اردو میں جوابی پیغام جو صارف فوری طور پر آگے بھیج سکے>",
  "knowledge_base_match": false
}}
"""


def classify_claim(claim: str) -> dict:
    """Full pipeline: retrieve context, classify with LLM, return structured result."""
    retrieved = retrieve_context(claim, top_k=3)

    # Check relevance: use top similarity score to decide if KB has useful context
    top_similarity = float(retrieved[0]["similarity"]) if retrieved else 0.0
    kb_match = top_similarity >= RELEVANCE_THRESHOLD

    if kb_match:
        context_text = "\n\n".join(
            f"- {doc['content_urdu']} (\u0645\u0627\u062e\u0630: {doc['source_url']})" for doc in retrieved
        )
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(claim=claim, context=context_text)
    else:
        prompt = NO_MATCH_PROMPT_TEMPLATE.format(claim=claim)

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
