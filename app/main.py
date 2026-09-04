"""
HealthGuard Urdu — FastAPI backend.

Scope (per project spec): text-in, text+audio-out. No image OCR, no ASR,
no WhatsApp/Telegram bot integration in this build.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse

from app.rag import call_llm, classify_claim, is_roman_script
from app.tts import text_to_speech_urdu

app = FastAPI(
    title="HealthGuard Urdu",
    description="Urdu health-misinformation classification via RAG, with Urdu TTS counter-message output.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Basic liveness check — confirms the API is running."""
    return {"status": "ok", "service": "healthguard-urdu"}


@app.get("/", response_class=HTMLResponse)
def demo_form():
    """Minimal HTML form for browser-based testing without Postman."""
    return """
    <html><body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
      <h2>HealthGuard Urdu — Demo</h2>
      <form action="/check-claim" method="post">
        <textarea name="claim" rows="4" style="width:100%;" dir="rtl"
          placeholder="\u06cc\u06c1\u0627\u06ba \u062f\u0639\u0648\u06cc\u0670 \u0644\u06a9\u06be\u06cc\u06ba..."></textarea><br><br>
        <button type="submit">Check Claim</button>
      </form>
    </body></html>
    """


@app.post("/check-claim")
def check_claim(claim: str = Form(...)):
    """Full pipeline: classify the claim via RAG, generate TTS audio, return HTML with player."""
    result = classify_claim(claim)
    audio_path = text_to_speech_urdu(result["counter_message_urdu"])
    audio_file = os.path.basename(audio_path)

    framing = result.get("cultural_framing_detected", [])
    sources = result.get("retrieved_sources", [])
    kb_match = result.get("knowledge_base_match", False)

    # Convert button initial state: offer the script the counter-message is NOT in
    if is_roman_script(claim):
        convert_target, convert_label = "urdu", "🔤 اردو رسم الخط میں دیکھیں"
    else:
        convert_target, convert_label = "roman", "🔤 Roman Urdu میں دیکھیں"

    # Build HTML result page with embedded audio player
    framing_html = "<br>".join(f"&bull; {f}" for f in framing) if framing else "<em>None detected</em>"

    # Parse source_url format: "citation text ||| url1; url2" -> citation + clickable links
    def source_line(s):
        raw = s.get("source_url", "")
        title = s["title"]
        if " ||| " in raw:
            citation, urls_part = raw.split(" ||| ", 1)
            urls = [u.strip() for u in urls_part.split(";") if u.strip()]
            links = " ".join(
                f'<a href="{u}" target="_blank" style="font-size:0.85em">[verify]</a>'
                for u in urls
            )
            return f"&bull; <strong>{title}</strong><br><small>{citation} {links}</small>"
        elif raw.startswith("http"):
            return f'&bull; <a href="{raw}" target="_blank">{title}</a>'
        else:
            return f"&bull; {title} <small>({raw})</small>"

    if kb_match and sources:
        sources_html = "<br>".join(source_line(s) for s in sources)
    else:
        sources_html = "<em>Not found in verified knowledge base &mdash; answer based on general medical caution.</em>"

    return HTMLResponse(content=f"""
    <html><body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;" dir="rtl">
      <h2>HealthGuard Urdu &mdash; Result</h2>
      <p><strong>Claim:</strong> {claim}</p>
      <p><strong>Category:</strong> {result['category']}</p>
      <p><strong>Confidence:</strong> {result['confidence_score']}%</p>
      <p><strong>KB match:</strong> {"Yes" if kb_match else "No"}</p>
      <p><strong>Cultural framing:</strong><br>{framing_html}</p>
      <p><strong>Counter-message:</strong><br>
        <span id="counter-message">{result['counter_message_urdu']}</span><br>
        <button onclick="convertScript()" id="convert-btn" data-target="{convert_target}"
          style="margin-top:6px;">{convert_label}</button>
      </p>
      <p><strong>Listen:</strong><br>
        <audio controls src="/audio/{audio_file}" style="width:100%; direction:ltr;">
          Your browser does not support audio.
        </audio>
      </p>
      <p><strong>Sources:</strong><br>{sources_html}</p>
      <hr>
      <a href="/">&larr; Check another claim</a>
      <script>
      async function convertScript() {{
        const msgEl = document.getElementById('counter-message');
        const btn = document.getElementById('convert-btn');
        const currentTarget = btn.dataset.target || 'urdu';
        btn.disabled = true;
        try {{
          const resp = await fetch('/transliterate', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
            body: `text=${{encodeURIComponent(msgEl.textContent)}}&target=${{currentTarget}}`
          }});
          const data = await resp.json();
          msgEl.textContent = data.converted;
          btn.dataset.target = currentTarget === 'urdu' ? 'roman' : 'urdu';
          btn.textContent = currentTarget === 'urdu' ? '🔤 Roman Urdu میں دیکھیں' : '🔤 اردو رسم الخط میں دیکھیں';
        }} finally {{
          btn.disabled = false;
        }}
      }}
      </script>
    </body></html>
    """)


@app.post("/transliterate")
def transliterate(text: str = Form(...), target: str = Form(...)):
    """Convert text between Roman Urdu and Urdu script on demand."""
    target_script = "رومن اردو (لاطینی رسم الخط)" if target == "roman" else "اردو رسم الخط"
    prompt = (
        f"درج ذیل متن کو {target_script} میں تبدیل کریں۔ "
        f"صرف تبدیل شدہ متن واپس کریں، کوئی وضاحت نہیں:\n\n{text}"
    )
    converted = call_llm(prompt, expect_json=False)
    return {"converted": converted.strip()}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    """Serve generated MP3 files from the audio_output/ directory."""
    filepath = Path(__file__).parent.parent / "audio_output" / filename
    if not filepath.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(filepath), media_type="audio/mpeg")
