# streamlit_app.py
"""
Flex Living - Reviews Dashboard (Streamlit)
- Fetches reviews from API
- Allows manager to toggle which reviews are shown publicly
- Saves manager choices locally in mock_reviews.json
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
import requests
from datetime import datetime
from pathlib import Path

# Path to logo
logo_path = Path("flex_logo.png")
st.sidebar.image(str(logo_path), use_container_width=True)

# Config
DATA_PATH = Path("mock_reviews.json")
API_URL = "https://the-flex-0fnb.onrender.com/api/reviews/hostaway"

st.set_page_config(page_title="Flex Living — Reviews Dashboard", layout="wide")

# ----------------- API Fetch -----------------
@st.cache_data(ttl=600)
def fetch_api_reviews():
    try:
        r = requests.get(API_URL, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.warning(f"API fetch error: {e}")
    return None

# ----------------- Load Data -----------------
@st.cache_data
def load_reviews_from_api_or_local():
    api_data = fetch_api_reviews()
    if api_data:
        raw = api_data
        source = "api"
    else:
        if DATA_PATH.exists():
            with DATA_PATH.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            source = "local"
        else:
            st.error("No API data and local mock_reviews.json not found.")
            st.stop()
    
    reviews = raw.get("data", raw.get("result", []))
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
        # parse date
        date_str = r.get("date") or r.get("created")
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            dt = pd.to_datetime(date_str, errors="coerce")
        base["date"] = dt
        # categories: flatten
        for cat in r.get("reviewCategory", []):
            base[f"cat_{cat.get('category')}"] = cat.get("rating")
        rows.append(base)
    
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["year_month"] = df["date"].dt.to_period("M").astype(str)
    
    return df, raw, source

def save_reviews(df, raw, path: Path):
    id_to_display = df.set_index("id")["displayOnWebsite"].to_dict()
    for r in raw.get("data", raw.get("result", [])):
        if r.get("id") in id_to_display:
            r["displayOnWebsite"] = bool(id_to_display[r.get("id")])
    with path.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, default=str)
    st.success(f"Saved {len(id_to_display)} review display flags to {path}")

# ----------------- Manager View -----------------
st.sidebar.markdown("---")
view_mode = st.sidebar.radio("View Mode", ["Manager Dashboard", "Public Property Page"])

df, raw_json, data_source = load_reviews_from_api_or_local()

if view_mode == "Manager Dashboard":
    st.title("Flex Living — Reviews Dashboard")
    st.write("Manager view • See per-property performance, filter reviews, and choose which reviews appear on the public website.")

    # Sidebar filters
    st.sidebar.markdown("---")
    st.sidebar.header("Filters & Controls")
    listings = ["All"] + sorted(df["listingName"].dropna().unique().tolist())
    selected_listing = st.sidebar.selectbox("Property", listings)
    channels = ["All"] + sorted(df["channel"].dropna().unique().tolist())
    selected_channel = st.sidebar.selectbox("Channel", channels)

    min_rating, max_rating = st.sidebar.slider("Rating range", 0.0, 10.0, (0.0, 10.0), step=0.5)
    category_cols = [c for c in df.columns if c.startswith("cat_")]
    categories = ["All"] + [c.replace("cat_", "") for c in category_cols if c]
    selected_category = st.sidebar.selectbox("Category", categories)
    start_date, end_date = st.sidebar.date_input("Date range", [df["date"].min().date(), df["date"].max().date()])
    search_text = st.sidebar.text_input("Search review text or guest name")

    # Sidebar save
    st.sidebar.markdown("---")
    if st.sidebar.button("Save display flags"):
        save_reviews(df, raw_json, DATA_PATH)

    # Filtering
    filtered = df.copy()
    if selected_listing != "All":
        filtered = filtered[filtered["listingName"] == selected_listing]
    if selected_channel != "All":
        filtered = filtered[filtered["channel"] == selected_channel]
    filtered = filtered[(filtered["rating"] >= min_rating) & (filtered["rating"] <= max_rating)]
    if selected_category != "All":
        colname = f"cat_{selected_category}"
        if colname in filtered.columns:
            filtered = filtered[filtered[colname].notna()]
        else:
            filtered = filtered.iloc[0:0]
    filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]
    if search_text:
        mask = filtered["publicReview"].fillna("").str.contains(search_text, case=False) | filtered["guestName"].fillna("").str.contains(search_text, case=False)
        filtered = filtered[mask]

    # Display reviews
    st.subheader("Reviews (filtered)")
    if filtered.empty:
        st.write("No reviews to show.")
    else:
        for _, row in filtered.sort_values("date", ascending=False).iterrows():
            cols = st.columns([6,1])
            with cols[0]:
                st.markdown(f"**{row['listingName']}** — {row['guestName']} • {row['date'].date() if pd.notna(row['date']) else 'Unknown date'}")
                st.write(f"**Rating:** {row['rating']} • **Channel:** {row['channel']}")
                if pd.notna(row.get("publicReview")):
                    st.write(row.get("publicReview"))
            with cols[1]:
                key = f"display_{int(row['id'])}"
                val = st.checkbox("Show", value=bool(row["displayOnWebsite"]), key=key)
                df.loc[df["id"] == row["id"], "displayOnWebsite"] = bool(val)

# ----------------- Public Property Page -----------------
elif view_mode == "Public Property Page":
    st.markdown(
        """
        <div style="
            background-color: #1b3b36; 
            padding: 16px 24px;
            border-radius: 8px;
            margin-bottom: 20px;
        ">
            <h2 style="color: white; margin: 0; font-weight: 500;">
                Flex Living — Property Page
            </h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("Public view • Reviews shown here are only those approved by managers.")

    properties = sorted(df["listingName"].dropna().unique().tolist())
    selected_property = st.selectbox("Select Property", properties)

    approved_reviews = df[
        (df["listingName"] == selected_property) &
        (df["displayOnWebsite"] == True)
    ].sort_values("date", ascending=False)

    st.subheader(selected_property)
    st.image("https://via.placeholder.com/800x400?text=Property+Image", use_container_width=True)  
    st.write("Property description and details would go here.")

    st.markdown("### Guest Reviews")
    if approved_reviews.empty:
        st.info("No reviews approved for this property yet.")
    else:
        for _, row in approved_reviews.iterrows():
            st.markdown(
                f"""
                <div style="
                    background-color: #ffffff;
                    border-radius: 16px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    border-left: 6px solid #1b3b36;
                ">
                    <h4 style="margin: 0; color:#333;">
                        ⭐ {int(row['rating']) if pd.notna(row['rating']) else 'N/A'}
                    </h4>
                    <p style="margin: 6px 0; font-size: 16px; color:#555;">
                        “{row['publicReview'] if row.get('publicReview') else ''}”
                    </p>
                    <p style="margin: 0; font-size: 14px; color:#888;">
                        — <b>{row['guestName']}</b> • {row['date'].date() if pd.notna(row['date']) else 'Unknown'}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

