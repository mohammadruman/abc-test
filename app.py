import streamlit as st
import pandas as pd
import os
import time
from job_scraper.core import crawl_jobs
from job_scraper.db_manager import query_jobs  # ✅ Add this import

st.set_page_config(page_title="Job Scraper", layout="centered")
st.title("🕷️ Job Scraper (with Live Logs + ChromaDB Integration)")
st.caption("Crawls Capgemini, Barclays, and Syngenta career pages — stores results in Excel and ChromaDB.")

# --- Input fields ---
start_url = st.text_input(
    "Career Site URL",
    "https://www.capgemini.com/in-en/careers/join-capgemini/job-search/?page=1",
)

skills = st.text_input(
    "Skills (comma-separated)",
    "",
    help="Leave blank to crawl all jobs",
)

max_jobs = st.number_input("Max jobs to crawl", min_value=1, max_value=500, value=20)
max_pages = st.number_input("Max pages to iterate (for pagination)", min_value=1, max_value=20, value=3)

if st.button("🚀 Start Crawling"):
    if not start_url.strip():
        st.error("Please enter a valid URL.")
    else:
        st.info("Starting job crawling... please wait ⏳")

        # Live placeholders
        progress_bar = st.progress(0)
        log_box = st.empty()
        status_box = st.empty()

        skills_list = [s.strip() for s in skills.split(",") if s.strip()]
        jobs = []
        extracted_count = 0

        try:
            st.write("🕷️ Crawling started... watching logs 👇")
            with st.spinner("Crawling pages..."):
                jobs = crawl_jobs(start_url, skills_list, int(max_jobs), int(max_pages))
                for i, job in enumerate(jobs, start=1):
                    extracted_count += 1
                    progress = i / max(len(jobs), 1)
                    progress_bar.progress(progress)
                    log_box.text_area(
                        "🔍 Live Extraction Log (temporary)",
                        value=f"Extracted job {i}/{len(jobs)}:\n{job.get('title', 'Unknown Title')}\nLink: {job.get('apply_url', '')}\n\n---",
                        height=250,
                    )
                    status_box.info(f"Currently extracting job {i}/{len(jobs)} ...")
                    time.sleep(0.25)

        except Exception as e:
            st.error(f"❌ Error during crawl: {e}")

        # --- After crawling ---
        if jobs:
            df = pd.DataFrame(jobs)
            os.makedirs("crawled_output", exist_ok=True)

            # ✅ Detect company from URL
            company = (
                "capgemini" if "capgemini.com" in start_url.lower()
                else "barclays" if "barclays" in start_url.lower()
                else "syngenta" if "syngenta" in start_url.lower()
                else "unknown"
            )

            file_path = f"crawled_output/{company}_jobs.xlsx"
            df.to_excel(file_path, index=False)
            st.success(f"✅ Extracted {len(df)} jobs and saved to `{file_path}`")
            st.dataframe(df.head(10))

            # ✅ Store in ChromaDB
            try:
                with st.spinner(f"Indexing {len(jobs)} {company} jobs into ChromaDB..."):
                    query_jobs(company, jobs)
                    st.info(f"✅ Stored {len(jobs)} {company} jobs in ChromaDB successfully.")
            except Exception as e:
                st.warning(f"⚠️ Failed to store in ChromaDB: {e}")

        else:
            st.warning("⚠️ No jobs found or matched filter.")
