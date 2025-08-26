import streamlit as st
import pandas as pd
import json

# Load mock data
def load_data():
    with open("mock_reviews.json", "r") as f:
        data = json.load(f)
    return data["result"]

# Convert JSON to DataFrame for easier handling
def json_to_df(data):
    rows = []
    for review in data:
        base = {
            "id": review["id"],
            "type": review["type"],
            "status": review["status"],
            "publicReview": review["publicReview"],
            "guestName": review["guestName"],
            "listingName": review["listingName"],
            "submittedAt": review["submittedAt"]
        }
        for cat in review["reviewCategory"]:
            row = base.copy()
            row["category"] = cat["category"]
            row["rating"] = cat["rating"]
            rows.append(row)
    return pd.DataFrame(rows)

# Main app
def main():
    st.title("📊 Reviews Dashboard")

    data = load_data()
    df = json_to_df(data)

    # Sidebar filters
    st.sidebar.header("Filters")
    guest_filter = st.sidebar.multiselect("Select Guest(s)", df["guestName"].unique())
    category_filter = st.sidebar.multiselect("Select Category", df["category"].unique())

    filtered_df = df.copy()
    if guest_filter:
        filtered_df = filtered_df[filtered_df["guestName"].isin(guest_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df["category"].isin(category_filter)]

    # Show reviews table
    st.subheader("Reviews")
    st.dataframe(filtered_df)

    # Aggregated ratings
    st.subheader("Average Ratings by Category")
    avg_ratings = filtered_df.groupby("category")["rating"].mean().reset_index()
    st.bar_chart(avg_ratings.set_index("category"))

    # Timeline of submissions
    st.subheader("Review Submission Timeline")
    timeline = pd.to_datetime(filtered_df["submittedAt"])
    timeline_df = pd.DataFrame({"submittedAt": timeline, "count": 1})
    timeline_df = timeline_df.groupby(timeline_df["submittedAt"].dt.date).count()
    st.line_chart(timeline_df)

if __name__ == "__main__":
    main()
