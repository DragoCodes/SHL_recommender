import pandas as pd
import requests
import streamlit as st

# Configure the app
st.set_page_config(
    page_title="SHL Assessment Recommender", page_icon="📊", layout="wide"
)

# API endpoint
API_URL = "http://localhost:8080/recommend"


def get_recommendations(query):
    """Call the recommendation API and return results"""
    try:
        response = requests.post(API_URL, json={"query": query})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return {"recommended_assessments": []}


def check_api_health():
    """Check if the API is available"""
    try:
        response = requests.get("http://localhost:8080/health")
        return response.status_code == 200
    except:
        return False


# App UI
st.title("SHL Assessment Recommendation System")

# Check API health
api_status = check_api_health()
if not api_status:
    st.error("⚠️ API is not available. Please ensure the API server is running.")
    st.stop()
else:
    st.success("✅ Connected to recommendation API")

st.markdown("""
This tool helps HR professionals and hiring managers find suitable SHL assessments for their needs.
Enter details about the position you're hiring for including skills, level, and any time constraints.
""")

with st.form("recommendation_form"):
    query = st.text_area(
        "Describe the position and requirements:",
        height=150,
        placeholder="Example: I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment that can be completed in 40 minutes.",
    )

    submitted = st.form_submit_button("Get Recommendations")

# Show example queries
with st.expander("Example queries you can try"):
    st.markdown("""
    - "Need assessment for entry-level sales role focusing on communication and resilience."
    - "Looking for technical assessments for senior Python developers who need to work in Agile teams."
    - "Recommend tests for finance managers with strong analytical skills and leadership abilities."
    - "Need quick assessments (under 30 minutes) for customer service representatives."
    """)

# Process form submission
if submitted and query:
    with st.spinner("Generating recommendations, please wait..."):
        # Get recommendations from API
        results = get_recommendations(query)

    if (
        results
        and "recommended_assessments" in results
        and results["recommended_assessments"]
    ):
        st.success(f"Found {len(results['recommended_assessments'])} recommendations!")

        # Display results in an attractive way
        for i, rec in enumerate(results["recommended_assessments"], 1):
            with st.container():
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.subheader(f"{i}. {rec.get('description', 'Unnamed Assessment')}")
                    st.markdown(
                        f"**Type:** {', '.join(rec.get('test_type', ['Unknown']))}"
                    )

                with col2:
                    st.markdown(
                        f"**Duration:** {rec.get('duration', 'Unknown')} minutes"
                    )
                    st.markdown(
                        f"**Remote Testing:** {rec.get('remote_support', 'Unknown')}"
                    )
                    st.markdown(
                        f"**Adaptive Support:** {rec.get('adaptive_support', 'Unknown')}"
                    )
                    if rec.get("url") and rec.get("url") != "Not Found":
                        st.markdown(f"[View Assessment]({rec['url']})")

                st.markdown("---")

        # Also provide a download option as CSV
        df = pd.DataFrame(results["recommended_assessments"])
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="shl_recommendations.csv",
            mime="text/csv",
        )
    else:
        st.warning(
            "No recommendations found. Try modifying your query to be more specific."
        )

# Footer
st.sidebar.header("About")
st.sidebar.markdown("""
This tool uses Retrieval Augmented Generation (RAG) to recommend SHL assessments based on your requirements.

It matches job requirements against a database of SHL assessments to find the most relevant options.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**Need help?** Contact your SHL representative for assistance.")

# Add system status indicators
st.sidebar.markdown("---")
st.sidebar.subheader("System Status")
col1, col2 = st.sidebar.columns(2)
with col1:
    st.markdown("API Status:")
with col2:
    if api_status:
        st.markdown("🟢 Online")
    else:
        st.markdown("🔴 Offline")
