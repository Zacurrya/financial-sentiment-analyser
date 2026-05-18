from fastapi import FastAPI
from pydantic import BaseModel

from transcript_processor import get_sentiment_score

app = FastAPI()

class TranscriptRequest(BaseModel):
    transcript: str

@app.post("/analyse")
def analyse(request: TranscriptRequest):
    sentiment_score = get_sentiment_score(request.transcript)
    return {
        "sentiment_score": round(sentiment_score, 4),
        "label": "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral"
    }