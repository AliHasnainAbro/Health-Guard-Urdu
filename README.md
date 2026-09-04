# Health-Guard-Urdu

**HealthGuard Urdu** is an AI-powered health-misinformation detection system for Urdu-language content in Pakistan. It takes a user-submitted health claim as **text**, classifies it against a vetted knowledge base using a RAG (Retrieval-Augmented Generation) pipeline, and returns a short, plain-Urdu counter-message as **text plus synthesized audio**.

Developed as a submission for the **2026 IEEE Technology Summit AI Founder Showcase** (Ideation track, Budapest, October 1–2, 2026) and adapted for the **Bano Qabil AI Hackathon Pakistan 2026**, hosted by Alkhidmat Foundation.

## Project Status

**Complete and working end-to-end.** The full pipeline — Urdu/Roman Urdu claim in, classified verdict + Urdu text counter-message + playable audio out — is implemented and tested across all three knowledge-base categories (polio vaccine, general vaccine, home remedies). A browser demo form is served at `/` for trying it without any API client.

- **RAG classification** — retrieval from a 12-document vetted Urdu knowledge base (Supabase + pgvector), with a per-document relevance threshold so weak sources never ride along a good match
- **Roman Urdu support** — LLM-based script normalization with ensemble retrieval, so `polio ke drops...` matches the same KB entries as پولیو کے قطرے...
- **Script-aware output** — the counter-message comes back in the script the user wrote in (Roman Urdu in → Roman Urdu out), with a one-click toggle to switch scripts
- **Verified sources** — every KB hit lists its citation with clickable `[verify]` links to the primary source
- **Urdu TTS** — audio counter-message via gTTS, playable inline in the demo page

## The Problem

Health misinformation spreads rapidly through Urdu-language social media — particularly WhatsApp, where forwarding is the default behavior. Most fact-checking tools target English content, leaving Urdu speakers with no quick way to verify the remedies, warnings, and "cures" that reach them daily. HealthGuard Urdu closes that gap: paste the claim, get a verdict and an audio reply you can forward right back.

## How It Works

1. **Input** — user submits a health claim as text: Urdu script or Roman Urdu (the script is auto-detected).
2. **Normalization** — Roman Urdu / English claims are transliterated into standard Urdu script (with established Urdu medical vocabulary) before retrieval, because multilingual embeddings score the two scripts very differently. Retrieval runs on up to three transliteration variants and keeps the best match.
3. **Retrieval** — the claim is embedded with `sentence-transformers` and matched against a vetted health-facts knowledge base stored in Supabase (Postgres + pgvector). Only documents clearing a similarity threshold are used.
4. **Classification** — the retrieved context plus the claim go to an LLM (Qwen), which returns a category, confidence score, detected cultural framing patterns (religious authority, traditional-remedy, anti-vaccine), and a short counter-message — in the script the user wrote in.
5. **Speech** — the counter-message is converted to Urdu audio via gTTS (Google Text-to-Speech).
6. **Response** — the API returns the classification, the counter-message text, and a playable audio file in one call.

If nothing in the knowledge base clears the relevance threshold, the system says so honestly (`KB match: No`, capped confidence, no fabricated sources) and answers from general medical caution.

### Scope of this build

Text-in, **text + audio-out**. No image OCR, no ASR (speech-to-text), and no WhatsApp/Telegram bot integration in this build.

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI + Uvicorn |
| Vector store | Supabase (Postgres + pgvector) |
| Embeddings | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim) |
| LLM classification | Qwen via Alibaba Cloud DashScope API |
| TTS | gTTS (Google Text-to-Speech, Urdu — no API key needed) |

## API Endpoints

| Method | Path | Description | Status |
| --- | --- | --- | --- |
| GET | `/` | Browser demo form (no API client needed) | Implemented |
| GET | `/health` | Liveness check | Implemented |
| POST | `/check-claim` | Full pipeline: classify + counter-message + audio in one call | Implemented |
| POST | `/transliterate` | On-demand conversion between Roman Urdu and Urdu script | Implemented |
| GET | `/audio/{filename}` | Serve a generated MP3 counter-message | Implemented |

## Getting Started

### Prerequisites

- Python 3.10+
- A Supabase project (URL + service-role key)
- An Alibaba Cloud Qwen API key (DashScope) for the LLM
- No TTS credentials needed (gTTS is free and keyless)

### Setup

```bash
git clone https://github.com/AliHasnainAbro/Health-Guard-Urdu.git
cd Health-Guard-Urdu

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env   # then fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, QWEN_API_KEY
```

### Knowledge base setup (one-time)

1. In the Supabase dashboard SQL editor, run `supabase/schema.sql` (creates the `healthguard_kb` table + pgvector index).
2. Run `supabase/match_function.sql` (creates the similarity-search function).
3. Embed and load the knowledge base:

```bash
python scripts/index_kb.py   # safe to re-run; clears rows before inserting
```

### Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs (Swagger UI) are then available at `http://127.0.0.1:8000/docs`, and the browser demo at `http://127.0.0.1:8000/`.

## Project Structure

```
Health-Guard-Urdu/
├── app/
│   ├── main.py          # FastAPI app: demo form, /check-claim, /transliterate, /audio
│   ├── rag.py           # RAG pipeline: normalization, retrieval, classification
│   └── tts.py           # gTTS Urdu text-to-speech
├── data/
│   ├── kb_documents.json           # 12-doc Urdu knowledge base
│   └── kb_sourcing_methodology.md  # source provenance audit trail
├── scripts/
│   └── index_kb.py      # embed + load KB into Supabase (re-runnable)
├── supabase/
│   ├── schema.sql       # healthguard_kb table + pgvector index
│   └── match_function.sql  # similarity-search function
├── audio_output/        # generated MP3s (gitignored)
├── .env.example
├── requirements.txt
├── LICENSE
└── README.md
```

## License

Released under the [MIT License](LICENSE) — Copyright (c) 2026 Ali Hasnain Abro.
