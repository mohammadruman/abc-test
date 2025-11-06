from .utils import sanitize_text

def extract_job_details(soup, url):
    title = soup.find("h1") or soup.find("h2") or soup.find("title")
    company = soup.find(class_="company") or soup.find("meta", {"name": "og:site_name"})
    location = soup.find(string=lambda t: "Location" in t) or soup.find(class_="location")
    desc = soup.find("div", class_="job-description") or soup.find("article") or soup.find("section")

    return {
        "job_id": url.split("/")[-1],
        "title": sanitize_text(title.get_text() if title else ""),
        "company": sanitize_text(company.get_text() if company and hasattr(company, "get_text") else "Capgemini"),
        "location": sanitize_text(location if isinstance(location, str) else getattr(location, "get_text", lambda: "")()),
        "application_link": url,
        "description": sanitize_text(desc.get_text() if desc else ""),
    }
