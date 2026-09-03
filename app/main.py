"""
HealthGuard Urdu — FastAPI backend.

Scope (per project spec): text-in, text+audio-out. No image OCR, no ASR,
no WhatsApp/Telegram bot integration in this build.
"""

from fastapi import FastAPI

app = FastAPI(
    title="HealthGuard Urdu",
    description="Urdu health-misinformation classification via RAG, with Urdu TTS counter-message output.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Basic liveness check — confirms the API is running before wiring in Supabase/LLM/TTS."""
    return {"status": "ok", "service": "healthguard-urdu"}


# Endpoints added in later steps:
# POST /classify     — Step 5 (RAG classification pipeline)
# POST /speak         — Step 6 (TTS)
# POST /check-claim   — Step 7 (combined endpoint: classify + TTS in one call)
