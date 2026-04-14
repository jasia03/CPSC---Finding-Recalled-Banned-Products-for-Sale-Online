import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# page configuration
st.set_page_config(
    page_title="CPSC Recall Finder",
    page_icon="🔍",
    layout="wide"
)

# title and description
st.title("🔍 CPSC Recall Finder Dashboard")
st.markdown("Identifying recalled and banned products listed for sale online")

# Step 1 — load data from database
@st.cache_data
def load_data():
    conn = sqlite3.connect('data/cpsc_recalls.db')
    matches = pd.read_sql("SELECT * FROM matches ORDER BY confidence_score DESC", conn)
    recalls = pd.read_sql("SELECT * FROM recalls", conn)
    conn.close()
    return matches, recalls

matches, recalls = load_data()

# Step 2 — summary metrics at the top
st.subheader("Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Listings Flagged", len(matches))
with col2:
    high_count = len(matches[matches['verdict'] == 'HIGH'])
    st.metric("High Confidence", high_count)
with col3:
    review_count = len(matches[matches['verdict'] == 'REVIEW'])
    st.metric("Needs Review", review_count)
with col4:
    st.metric("Recalled Products in DB", len(recalls))

    # Step 3 — filters
st.subheader("Filters")

col1, col2, col3 = st.columns(3)

with col1:
    verdict_filter = st.multiselect(
        "Filter by verdict",
        options=['HIGH', 'REVIEW', 'LOW'],
        default=['HIGH', 'REVIEW']
    )

with col2:
    min_confidence = st.slider(
        "Minimum confidence score",
        min_value=0,
        max_value=100,
        value=50
    )

with col3:
    platforms = ['All'] + sorted(matches['platform'].dropna().unique().tolist())
    platform_filter = st.selectbox(
        "Filter by platform",
        options=platforms
    )
# category filter
categories = ['All'] + sorted(matches['Category'].dropna().unique().tolist()) if 'Category' in matches.columns else ['All']
category_filter = st.selectbox(
    "Filter by product category",
    options=categories
)

# apply filters
filtered = matches[
    (matches['verdict'].isin(verdict_filter)) &
    (matches['confidence_score'] >= min_confidence)
]

if category_filter != 'All':
    filtered = filtered[filtered['Category'] == category_filter]

if platform_filter != 'All':
    filtered = filtered[filtered['platform'] == platform_filter]

st.caption(f"Showing {len(filtered)} of {len(matches)} flagged listings")

# Step 4 — color coded listings table
st.subheader("Flagged Listings")

def color_verdict(val):
    if val == 'HIGH':
        return 'background-color: #ffcccc; color: #8b0000'
    elif val == 'REVIEW':
        return 'background-color: #fff3cc; color: #7d6608'
    else:
        return 'background-color: #e8f5e9; color: #1b5e20'

def color_confidence(val):
    if val >= 70:
        return 'color: #8b0000; font-weight: bold'
    elif val >= 50:
        return 'color: #7d6608; font-weight: bold'
    else:
        return 'color: #1b5e20'

display_cols = [
    'listing_title',
    'recalled_product',
    'manufacturer',
    'Category',
    'confidence_score',
    'verdict',
    'hazard',
    'url'
]
styled_table = filtered[display_cols].style\
    .map(color_verdict, subset=['verdict'])\
    .map(color_confidence, subset=['confidence_score'])

st.dataframe(
    styled_table,
    column_config={
        "url": st.column_config.LinkColumn(
            "listing link",
            display_text="open on eBay"
        )
    },
    width='stretch',
    height=300
)

# Step 5 — analytics charts
st.subheader("Analytics")

col1, col2 = st.columns(2)

with col1:
    # verdict breakdown pie chart
    verdict_counts = matches['verdict'].value_counts().reset_index()
    verdict_counts.columns = ['Verdict', 'Count']
    
    fig1 = px.pie(
        verdict_counts,
        values='Count',
        names='Verdict',
        title='Listings by Verdict',
        color='Verdict',
        color_discrete_map={
            'HIGH': '#ff4444',
            'REVIEW': '#ffaa00',
            'LOW': '#44bb44'
        }
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # confidence score distribution bar chart
    fig2 = px.histogram(
        matches,
        x='confidence_score',
        nbins=10,
        title='Confidence Score Distribution',
        labels={'confidence_score': 'Confidence Score', 'count': 'Number of Listings'},
        color_discrete_sequence=['#4F46E5']
    )
    st.plotly_chart(fig2, use_container_width=True)

# Step 6 — listing detail panel
st.subheader("Listing Detail")
st.caption("Select a listing to see full details and take action")

selected_listing = st.selectbox(
    "Choose a listing to review",
    options=filtered['listing_title'].tolist()
)

if selected_listing:
    detail = filtered[filtered['listing_title'] == selected_listing].iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Listing Information**")
        st.write(f"**Title:** {detail['listing_title']}")
        st.write(f"**Confidence Score:** {detail['confidence_score']}%")
        st.write(f"**Verdict:** {detail['verdict']}")
        st.write(f"**Scoring Breakdown:** {detail['reasons']}")
    
    with col2:
        st.markdown("**Matched Recall Information**")
        st.write(f"**Recalled Product:** {detail['recalled_product']}")
        st.write(f"**Manufacturer:** {detail['manufacturer']}")
        st.write(f"**Recall Number:** {detail['recall_number']}")
        st.write(f"**Hazard:** {detail['hazard']}")
    
    # action buttons
    st.markdown("**Reviewer Actions**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Confirm Match", type="primary"):
            st.success("Match confirmed and flagged for removal request")
    
    with col2:
        if st.button("❌ False Positive"):
            st.warning("Marked as false positive and removed from queue")
    
    with col3:
        if detail['url']:
            st.link_button("🔍 View on eBay", detail['url'])
        else:
            st.button("🔍 View on eBay", disabled=True)

# Step 7 — export button
st.subheader("Export")
st.caption("Download flagged listings for removal requests")

export_df = filtered[display_cols].copy()
csv = export_df.to_csv(index=False)

st.download_button(
    label="Download flagged listings as CSV",
    data=csv,
    file_name="cpsc_flagged_listings.csv",
    mime="text/csv"
)

# Sellers Tab
st.divider()
st.subheader("Flagged Sellers")
st.caption("Sellers with multiple recalled product listings — potential repeat offenders")

# load seller data
@st.cache_data
def load_sellers():
    conn = sqlite3.connect('data/cpsc_recalls.db')
    try:
        sellers = pd.read_sql("SELECT * FROM seller_flags ORDER BY high_confidence DESC", conn)
    except:
        sellers = pd.DataFrame()
    conn.close()
    return sellers

sellers = load_sellers()

if len(sellers) == 0:
    st.info("Run matcher/seller_analysis.py to generate seller data")
else:
    # seller summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Flagged Sellers", len(sellers))
    with col2:
        high_risk = len(sellers[sellers['risk_level'] == 'HIGH RISK'])
        st.metric("High Risk Sellers", high_risk)
    with col3:
        medium_risk = len(sellers[sellers['risk_level'] == 'MEDIUM RISK'])
        st.metric("Medium Risk Sellers", medium_risk)

    # seller risk filter
    risk_filter = st.multiselect(
        "Filter by risk level",
        options=['HIGH RISK', 'MEDIUM RISK', 'LOW RISK'],
        default=['HIGH RISK', 'MEDIUM RISK']
    )

    filtered_sellers = sellers[sellers['risk_level'].isin(risk_filter)]
    st.caption(f"Showing {len(filtered_sellers)} sellers")

    # color code risk level
    def color_risk(val):
        if val == 'HIGH RISK':
            return 'background-color: #ffcccc; color: #8b0000'
        elif val == 'MEDIUM RISK':
            return 'background-color: #fff3cc; color: #7d6608'
        else:
            return 'background-color: #e8f5e9; color: #1b5e20'

    display_seller_cols = [
        'seller_username',
        'total_flagged',
        'high_confidence',
        'risk_level',
        'feedback_score',
        'feedback_pct',
        'recalled_products',
        'ebay_profile'
    ]

    styled_sellers = filtered_sellers[display_seller_cols].style\
        .map(color_risk, subset=['risk_level'])

    st.dataframe(
        styled_sellers,
        column_config={
            "ebay_profile": st.column_config.LinkColumn(
                "eBay profile",
                display_text="view seller"
            )
        },
        width='stretch',
        height=400
    )

    # export sellers
    seller_csv = filtered_sellers[display_seller_cols].to_csv(index=False)
    st.download_button(
        label="Download flagged sellers as CSV",
        data=seller_csv,
        file_name="cpsc_flagged_sellers.csv",
        mime="text/csv"
    )