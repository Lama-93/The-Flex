# import streamlit as st

# st.title("🎈 123")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )
import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Load mock reviews
with open("mock_reviews.json", "r") as f:
    reviews = json.load(f)

df = pd.DataFrame(reviews)

st.set_page_config(page_title="F Living Reviews Dashboard", layout="wide")

st.title("🏘️ F Living Reviews Dashboard")
st.write("Manager view of property performance based on guest reviews.")

# Sidebar filters
st.sidebar.header("🔎 Filters")
property_filter = st.sidebar.multiselect("Select Property", df["property_name"].unique())
channel_filter = st.sidebar.multiselect("Select Channel", df["channel"].unique())
rating_filter = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.1)

filtered_df = df.copy()
if property_filter:
    filtered_df = filtered_df[filtered_df["property_name"].isin(property_filter)]
if channel_filter:
    filtered_df = filtered_df[filtered_df["channel"].isin(channel_filter)]
filtered_df = filtered_df[filtered_df["rating"] >= rating_filter]

# Metrics
st.subheader("📊 Summary Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Reviews", len(filtered_df))
col2.metric("Avg. Rating", round(filtered_df["rating"].mean(), 2) if not filtered_df.empty else "N/A")
col3.metric("Approved Reviews", filtered_df["approved"].sum())

# Trend chart
st.subheader("📈 Rating Trend Over Time")
if not filtered_df.empty:
    trend = px.line(filtered_df, x="date", y="rating", color="property_name", markers=True)
    st.plotly_chart(trend, use_container_width=True)
else:
    st.info("No data matches the filters.")

# Reviews Table
st.subheader("📝 Reviews")
st.dataframe(filtered_df[["property_name", "channel", "rating", "date", "comment", "approved"]])

# Approve/Unapprove Reviews
st.subheader("✅ Manage Approvals")
for idx, row in filtered_df.iterrows():
    approved = st.checkbox(f"{row['property_name']} - {row['comment'][:40]}...", value=row["approved"])
    df.loc[idx, "approved"] = approved
