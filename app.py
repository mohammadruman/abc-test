import streamlit as st
import pandas as pd
import os
import time
from job_scraper.core import crawl_jobs

st.set_page_config(page_title="Job Scraper", layout="centered")
st.title("🕷️ Job Scraper (Debug Mode)")
st.caption("Temporary debug version — shows real-time extraction logs on page")

# Input fields
start_url = st.text_input(
    "Career Site URL",
    "https://www.capgemini.com/in-en/careers/join-capgemini/job-search/?page=1",
)

skills = st.text_input(
    "Skills (comma-separated)",
    "",
    help="Leave blank to crawl all jobs",
)

max_jobs = st.number_input("Max jobs to crawl", min_value=1, max_value=500, value=10)
max_pages = st.number_input("Max pages to iterate (for pagination)", min_value=1, max_value=20, value=3)

if st.button("🚀 Start Crawling"):
    if not start_url.strip():
        st.error("Please enter a valid URL.")
    else:
        st.info("Starting job crawling... please wait ⏳")

        # Create live placeholders
        progress_bar = st.progress(0)
        log_box = st.empty()  # Will hold log messages
        status_box = st.empty()  # Will show current status

        # Collect skills
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]

        # Run crawler
        jobs = []
        extracted_count = 0
        try:
            # We call crawl_jobs and simulate live logging
            st.write("🕷️ Crawling started... watching logs 👇")
            with st.spinner("Crawling pages..."):
                jobs = crawl_jobs(start_url, skills_list, int(max_jobs), int(max_pages))
                # Simulate loop logs (since the actual crawling runs in subprocess)
                for i, job in enumerate(jobs, start=1):
                    extracted_count += 1
                    progress = i / len(jobs)
                    progress_bar.progress(progress)
                    log_box.text_area(
                        "🔍 Live Extraction Log (temporary)",
                        value=f"Extracted job {i}/{len(jobs)}:\n{job.get('title', 'Unknown Title')}\nLink: {job.get('application_link', '')}\n\n---",
                        height=250,
                    )
                    status_box.info(f"Currently extracting job {i}/{len(jobs)} ...")
                    time.sleep(0.3)
        except Exception as e:
            st.error(f"❌ Error during crawl: {e}")

        # After crawling
        if jobs:
            df = pd.DataFrame(jobs)
            os.makedirs("crawled_output", exist_ok=True)
            site_name = start_url.split("/")[2].split(".")[0]
            file_path = f"crawled_output/{site_name}_jobs.xlsx"
            df.to_excel(file_path, index=False)
            st.success(f"✅ Extracted {len(df)} jobs and saved to `{file_path}`")
            st.dataframe(df)
        else:
            st.warning("⚠️ No jobs found or matched filter.")
