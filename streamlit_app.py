# streamlit_app.py
"""
Flex Living - Reviews Dashboard (Streamlit)
Single-file app that:
- Loads mocked Hostaway JSON (mock_reviews.json)
- Normalizes & displays per-listing metrics
- Allows filtering by rating, channel, category, date range
- Shows trends (monthly average rating)
- Lets manager toggle which reviews are shown on the public website and save changes locally
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
from datetime import datetime
from pathlib import Path

DATA_PATH = Path("mock_reviews.json")

st.set_page_config(page_title="Flex Living — Reviews Dashboard", layout="wide")

@st.cache_data
def load_reviews(path: Path):
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    reviews = raw.get("result", [])
    # Normalize to DataFrame
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
        date_str = r.get("date")
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception:
            dt = None
        base["date"] = dt
        # categories: convert to dict of category->rating (flatten)
        cat_list = r.get("reviewCategory", [])
        for cat in cat_list:
            base[f"cat_{cat.get('category')}"] = cat.get("rating")
        rows.append(base)
    df = pd.DataFrame(rows)
    # ensure date dtype and derived columns
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    return df, reviews

def save_reviews(original_raw, df, path: Path):
    # map displayOnWebsite changes back to original_raw by id
    id_to_display = df.set_index("id")["displayOnWebsite"].to_dict()
    for r in original_raw.get("result", []):
        if r.get("id") in id_to_display:
            r["displayOnWebsite"] = bool(id_to_display[r.get("id")])
    with path.open("w", encoding="utf-8") as f:
        json.dump(original_raw, f, indent=2, default=str)
    st.success(f"Saved {len(id_to_display)} review display flags to {path}")

# UI layout
st.title("Flex Living — Reviews Dashboard")
st.write("Manager view • See per-property performance, filter reviews, and choose which reviews appear on the public website.")

# Load data
try:
    df, raw_json = load_reviews(DATA_PATH)
except FileNotFoundError:
    st.error(f"Mock data not found: {DATA_PATH}. Add `mock_reviews.json` to the same folder as this app.")
    st.stop()

# Sidebar: filters
st.sidebar.header("Filters & Controls")
listings = ["All"] + sorted(df["listingName"].dropna().unique().tolist())
selected_listing = st.sidebar.selectbox("Property (listing)", listings, index=0)
channels = ["All"] + sorted(df["channel"].dropna().unique().tolist())
selected_channel = st.sidebar.selectbox("Channel", channels, index=0)

min_rating, max_rating = st.sidebar.slider("Rating range", 0.0, 10.0, (0.0, 10.0), step=0.5)

# categories discovered dynamically
category_cols = [c for c in df.columns if c.startswith("cat_")]
categories = ["All"] + [c.replace("cat_", "") for c in category_cols]
selected_category = st.sidebar.selectbox("Category (review score)", categories, index=0)

date_min = df["date"].min()
date_max = df["date"].max()
start_date, end_date = st.sidebar.date_input("Date range", [date_min.date(), date_max.date()])

search_text = st.sidebar.text_input("Search review text or guest name")

st.sidebar.markdown("---")
st.sidebar.write("Save changes to `displayOnWebsite` locally:")
if st.sidebar.button("Save display flags (local file)"):
    save_reviews(raw_json, df, DATA_PATH)

st.sidebar.write("Note: Streamlit Cloud file persistence depends on repo settings. Local changes save to mock_reviews.json in app folder.")

# Apply filters
filtered = df.copy()
if selected_listing != "All":
    filtered = filtered[filtered["listingName"] == selected_listing]
if selected_channel != "All":
    filtered = filtered[filtered["channel"] == selected_channel]
filtered = filtered[(filtered["rating"] >= min_rating) & (filtered["rating"] <= max_rating)]
if selected_category != "All":
    colname = f"cat_{selected_category}"
    if colname in filtered.columns:
        filtered = filtered[filtered[colname].notna()]  # only reviews that include that category
    else:
        filtered = filtered.iloc[0:0]  # no matches
# date range
filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]
if search_text:
    mask = filtered["publicReview"].fillna("").str.contains(search_text, case=False, na=False) | filtered["guestName"].fillna("").str.contains(search_text, case=False, na=False)
    filtered = filtered[mask]

# Top-level KPIs
col1, col2, col3, col4 = st.columns([2,2,2,2])
with col1:
    st.metric("Properties", value=len(df["listingId"].unique()))
with col2:
    st.metric("Total reviews (all time)", value=len(df))
with col3:
    avg_rating = round(filtered["rating"].mean(), 2) if not filtered.empty else "N/A"
    st.metric("Avg rating (filtered)", value=avg_rating)
with col4:
    percent_displayed = round(100 * filtered["displayOnWebsite"].mean(), 1) if not filtered.empty else 0
    st.metric("% shown on website (filtered)", value=f"{percent_displayed}%")

st.markdown("---")

# Left: charts. Right: review list + toggles
left, right = st.columns([2,3])

with left:
    st.subheader("Trends & Distributions")

    if not filtered.empty:
        # monthly average rating chart
        trend = filtered.groupby("year_month").agg(avg_rating=("rating","mean"), count=("id","count")).reset_index()
        chart = alt.Chart(trend).transform_calculate(month='datum.year_month').mark_line(point=True).encode(
            x=alt.X('year_month:T', title='Month'),
            y=alt.Y('avg_rating:Q', title='Avg rating'),
            tooltip=['year_month', alt.Tooltip('avg_rating:Q', format=".2f"), 'count']
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)

        # rating distribution histogram
        hist = alt.Chart(filtered).mark_bar().encode(
            alt.X("rating:Q", bin=alt.Bin(step=0.5), title="Rating"),
            y='count()',
            tooltip=[alt.Tooltip('count()', title='Number')]
        ).properties(height=200)
        st.altair_chart(hist, use_container_width=True)
    else:
        st.info("No reviews match your filters.")

    # per-property summary table
    st.subheader("Per-property performance")
    summary = filtered.groupby("listingName").agg(
        avg_rating=("rating","mean"),
        reviews=("id","count"),
        pct_displayed=("displayOnWebsite", "mean")
    ).reset_index()
    if not summary.empty:
        summary["avg_rating"] = summary["avg_rating"].round(2)
        summary["pct_displayed"] = (summary["pct_displayed"] * 100).round(1).astype(str) + "%"
        st.dataframe(summary.sort_values(["avg_rating","reviews"], ascending=[False, False]), height=220)
    else:
        st.write("No property matches filters.")

with right:
    st.subheader("Reviews (filtered)")
    if filtered.empty:
        st.write("No reviews to show.")
    else:
        # Show reviews with toggles (paged)
        page_size = 8
        total = len(filtered)
        page = st.number_input("Page", min_value=1, max_value=(total-1)//page_size + 1, value=1, step=1)
        start = (page-1)*page_size
        end = start + page_size
        page_df = filtered.sort_values("date", ascending=False).iloc[start:end].copy()

        for idx, row in page_df.iterrows():
            box = st.container()
            with box:
                cols = st.columns([6,1])
                with cols[0]:
                    st.markdown(f"**{row['listingName']}** — {row['guestName']} • {row['date'].date() if pd.notna(row['date']) else 'Unknown date'}")
                    st.write(f"**Rating:** {row['rating'] if pd.notna(row['rating']) else 'N/A'} • **Channel:** {row['channel']} • **Type:** {row['type']}")
                    if pd.notna(row.get("publicReview")) and row.get("publicReview"):
                        st.write(row.get("publicReview"))
                    # show categories
                    cats = {c.replace("cat_",""): row[c] for c in page_df.columns if c.startswith("cat_") and pd.notna(row.get(c))}
                    if cats:
                        cat_line = " • ".join([f"{k}: {int(v) if pd.notna(v) else 'N/A'}" for k,v in cats.items()])
                        st.caption(cat_line)
                with cols[1]:
                    key = f"display_{int(row['id'])}"
                    val = st.checkbox("Show", value=bool(row["displayOnWebsite"]), key=key)
                    # write back to df
                    df.loc[df["id"] == row["id"], "displayOnWebsite"] = bool(val)

        st.markdown(f"Showing {start+1}-{min(end,total)} of {total} reviews (filtered).")

st.markdown("---")
st.info("Tip: Press Save in the sidebar to write display flags to `mock_reviews.json`. When deploying to Streamlit Cloud, saving to the repo depends on how you configure storage — for a production app you'd push the changes to a backend service or database.")

st.caption("Built for the Flex Living developer assessment. Contact the product owner to wire this to a real Hostaway integration and a persistent DB.")
