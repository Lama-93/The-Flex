from fastapi import FastAPI
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

app = FastAPI(title="Flex Living Reviews API")
DATA_PATH = Path("mock_reviews.json")

# Normalize function
def normalize_reviews(raw_json):
    reviews = raw_json.get("result", [])
    rows = []
    for r in reviews:
        base = {
            "id": r.get("id"),
            "listingId": r.get("listingId"),
            "listingName": r.get("listingName"),
            "type": r.get("type"),
            "status": r.get("status"),
            "rating": r.get("rating"),
            "publicReview": r.get("publicReview"),
            "channel": r.get("channel"),
            "channelId": r.get("channelId"),
            "guestName": r.get("guestName"),
            "displayOnWebsite": r.get("displayOnWebsite", False),
        }
        date_str = r.get("date") or r.get("created")
        try:
            base["date"] = datetime.fromisoformat(date_str).isoformat()
        except Exception:
            base["date"] = date_str
        for cat in r.get("reviewCategory", []):
            base[f"cat_{cat.get('category')}"] = cat.get("rating")
        rows.append(base)
    return rows

# API route
@app.get("/api/reviews/hostaway")
def get_reviews():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    normalized = normalize_reviews(raw)
    return {"status": "success", "data": normalized}
