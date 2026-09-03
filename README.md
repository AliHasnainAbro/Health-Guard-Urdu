# Health-Guard-Urdu

**HealthGuard Urdu** is an AI-powered health-misinformation detection system for Urdu-language content in Pakistan. It takes a user-submitted health claim as **text**, classifies it against a vetted knowledge base using a RAG (Retrieval-Augmented Generation) pipeline, and returns a short, plain-Urdu counter-message as **text plus synthesized audio**.

Developed as a submission for the **2026 IEEE Technology Summit AI Founder Showcase** (Ideation track, Budapest, October 1–2, 2026) and adapted for the **Bano Qabil AI Hackathon Pakistan 2026**, hosted by Alkhidmat Foundation.

## The Problem

Health misinformation spreads rapidly through Urdu-language social media — particularly WhatsApp, where forwarding is the default behavior. Most fact-checking tools target English content, leaving Urdu speakers with no quick way to verify the remedies, warnings, and "cures" that reach them daily. HealthGuard Urdu closes that gap: paste the claim, get a verdict and an audio reply you can forward right back.

## How It Works

1. **Input** — user submits an Urdu (or Roman Urdu) health claim as text.
2. **Retrieval** — the claim is embedded with `sentence-transformers` and matched against a vetted health-facts knowledge base stored in Supabase (Postgres + pgvector).
3. **Classification** — the retrieved context plus the claim are passed to an LLM (Qwen), which labels the claim (e.g., accurate / misleading / unverifiable) with a brief justification.
4. **Counter-message** — a short, plain-Urdu correction is generated.
5. **Speech** — the counter-message is converted to natural-sounding Urdu audio via Alibaba Cloud Intelligent Speech Interaction (TTS).
6. **Response** — the API returns the classification, the Urdu text, and the audio in one call.

### Scope of this build

Text-in, **text + audio-out**. No image OCR, no ASR (speech-to-text), and no WhatsApp/Telegram bot integration in this build.

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI + Uvicorn |
| Vector store | Supabase (Postgres + pgvector) |
| Embeddings | sentence-transformers |
| LLM classification | Qwen (Qoder built-in model access or Alibaba Cloud API) |
| TTS | Alibaba Cloud Intelligent Speech Interaction (Urdu) |

## API Endpoints

| Method | Path | Description | Status |
| --- | --- | --- | --- |
| GET | `/health` | Liveness check | Implemented |
| POST | `/classify` | RAG classification pipeline | Step 5 |
| POST | `/speak` | Urdu text-to-speech | Step 6 |
| POST | `/check-claim` | Combined classify + TTS in one call | Step 7 |

## Getting Started

### Prerequisites

- Python 3.10+
- A Supabase project (URL + service-role key)
- Alibaba Cloud Intelligent Speech Interaction credentials (for TTS)

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

cp .env.example .env   # then fill in your keys
```

### Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs (Swagger UI) are then available at `http://127.0.0.1:8000/docs`.

## Project Structure

```
Health-Guard-Urdu/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI app + endpoints
├── data/                # knowledge base / seed data
├── .env.example         # environment variable template
├── requirements.txt
├── LICENSE
└── README.md
```

## License

Released under the [MIT License](LICENSE) — Copyright (c) 2026 Ali Hasnain Abro.
