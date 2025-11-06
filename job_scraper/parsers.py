from urllib.parse import urljoin, urlparse

def capgemini_parser(soup, base):
    """
    Extract job posting links from Capgemini's career pages.
    Works with both API-based and HTML-rendered job listings.
    """
    links = []

    # 1️⃣ Capgemini's job listings appear inside cards with href="/in-en/jobs/xxxxx"
    for a in soup.select("a[href*='/in-en/jobs/']"):
        href = a.get("href")
        if href and "/in-en/jobs/" in href:
            links.append(urljoin(base, href))

    # 2️⃣ Fallback for older layout
    if not links:
        for a in soup.select("a[href*='/jobs/']"):
            href = a.get("href")
            if href and "capgemini.com" not in href:
                links.append(urljoin(base, href))

    return list(set(links))


def barclays_parser(soup, base):
    return [urljoin(base, a["href"]) for a in soup.select("a[href*='/job/']")]


def syngenta_parser(soup, base):
    return [urljoin(base, a["href"]) for a in soup.select("a[href*='/jobs/']")]


def generic_parser(soup, base):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(k in href for k in ["job", "career", "apply", "vacancy"]):
            links.append(urljoin(base, a["href"]))
    return list(set(links))


def get_job_links(soup, start_url):
    domain = urlparse(start_url).netloc.lower()
    if "capgemini" in domain:
        return capgemini_parser(soup, start_url)
    elif "barclays" in domain:
        return barclays_parser(soup, start_url)
    elif "syngenta" in domain:
        return syngenta_parser(soup, start_url)
    else:
        return generic_parser(soup, start_url)
