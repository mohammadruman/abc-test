import streamlit as st
from job_scraper.db_manager import query_jobs

st.set_page_config(page_title="Semantic Job Search", layout="centered")
st.title("🔍 Semantic Job Search (via ChromaDB)")
st.caption("Search across Capgemini, Barclays, and Syngenta jobs using natural language.")

company = st.selectbox("Select company (optional)", ["All", "Capgemini", "Barclays", "Syngenta"])
query_text = st.text_input("Enter search query", "Python developer")

if st.button("Search"):
    st.info("Searching in ChromaDB... ⏳")

    company_name = None if company == "All" else company

    # 1️⃣ Search top matches
    results = query_jobs(company_name=company_name, query_text=query_text, n_results=10)

    # 2️⃣ Get total count of matches
    total_count = query_jobs(company_name=company_name, query_text=query_text, count_only=True)

    st.subheader(f"🔢 Total matching jobs: {total_count}")

    if results:
        st.success(f"Top {len(results)} semantic matches:")
        for r in results:
            st.markdown(f"""
            **{r['title']}**  
            🏢 {r['company']}  
            📍 {r['location']}  
            🔗 [View Job]({r['url']})  
            _{r['preview']}_  
            ---
            """)
    else:
        st.warning("No matching jobs found.")
