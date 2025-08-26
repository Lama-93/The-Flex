import json
import pandas as pd

# Load JSON data
with open("mock_reviews.json", "r") as f:
    data = json.load(f)


reviews = data["result"]

# Normalize JSON into DataFrame
rows = []
for r in reviews:
    base = {
        "review_id": r["id"],
        "listing_id": r["listing_id"],
        "type": r["type"],
        "status": r["status"],
        "overall_rating": r["rating"],
        "publicReview": r["publicReview"],
        "channel": r["channel"],
        "date": pd.to_datetime(r["date"])
    }
    
    # If review has categories, expand them
    if r["reviewCategory"]:
        for cat in r["reviewCategory"]:
            row = base.copy()
            row["category"] = cat["category"]
            row["category_rating"] = cat["rating"]
            rows.append(row)
    else:
        # For host-to-guest reviews without categories
        row = base.copy()
        row["category"] = None
        row["category_rating"] = None
        rows.append(row)

df = pd.DataFrame(rows)

print(df.head())
