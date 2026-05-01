import requests
from beautifulsoup4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    """Remove extra whitespace and blank lines."""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def scrape_linkedin(soup):
    selectors = [
        "div.description__text",
        "div.show-more-less-html__markup",
        "section.description",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator="\n")
    return None


def scrape_naukri(soup):
    selectors = [
        "div.job-desc",
        "div.dang-inner-html",
        "section.job-desc",
        "div.description",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator="\n")
    return None


def scrape_internshala(soup):
    selectors = [
        "div.internship_details",
        "div#about_internship",
        "div.about-section",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator="\n")
    return None


def scrape_wellfound(soup):
    selectors = [
        "div.job-description",
        "div[class*='jobDescription']",
        "section[class*='description']",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator="\n")
    return None


def scrape_generic(soup):
    """
    Fallback: find the largest block of text on the page.
    Works on most company career pages.
    """
    # Remove nav, header, footer, scripts, styles
    for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    # Common job description container patterns
    candidates = []

    # Try common class/id names
    patterns = [
        "job-description", "jobDescription", "job_description",
        "job-details", "jobDetails", "job_details",
        "job-content", "jobContent",
        "description", "details", "content",
        "posting-requirements", "requirements",
    ]

    for pattern in patterns:
        for el in soup.find_all(
            True,
            {"class": re.compile(pattern, re.I)}
        ):
            text = el.get_text(separator="\n").strip()
            if len(text) > 200:
                candidates.append((len(text), text))

        for el in soup.find_all(
            True,
            {"id": re.compile(pattern, re.I)}
        ):
            text = el.get_text(separator="\n").strip()
            if len(text) > 200:
                candidates.append((len(text), text))

    if candidates:
        # Return the largest matching block
        candidates.sort(reverse=True)
        return candidates[0][1]

    # Last resort: get all paragraph text
    paragraphs = soup.find_all("p")
    text = "\n".join(p.get_text() for p in paragraphs if len(p.get_text()) > 50)
    if len(text) > 200:
        return text

    return None


def scrape_job_description(url: str) -> dict:
    """
    Main function. Pass any job URL, get back the JD text.

    Returns:
        {
            "success": True/False,
            "url": original url,
            "site": detected site name,
            "text": cleaned job description text,
            "error": error message if failed
        }
    """
    result = {"success": False, "url": url, "site": "unknown", "text": "", "error": ""}

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        result["error"] = f"Failed to fetch URL: {e}"
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    # Detect site and use specific scraper
    domain = url.lower()
    raw_text = None

    if "linkedin.com" in domain:
        result["site"] = "LinkedIn"
        raw_text = scrape_linkedin(soup)
    elif "naukri.com" in domain:
        result["site"] = "Naukri"
        raw_text = scrape_naukri(soup)
    elif "internshala.com" in domain:
        result["site"] = "Internshala"
        raw_text = scrape_internshala(soup)
    elif "wellfound.com" in domain or "angel.co" in domain:
        result["site"] = "Wellfound"
        raw_text = scrape_wellfound(soup)
    else:
        result["site"] = "Generic"
        raw_text = scrape_generic(soup)

    # If site-specific scraper failed, try generic fallback
    if not raw_text and result["site"] != "Generic":
        raw_text = scrape_generic(soup)

    if raw_text and len(raw_text.strip()) > 100:
        result["success"] = True
        result["text"] = clean_text(raw_text)
    else:
        result["error"] = (
            "Could not extract job description. "
            "The site may require login or use JavaScript rendering."
        )

    return result


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":
    # Replace with any real job URL to test
    test_url = input("Paste a job URL to test: ").strip()

    print(f"\nScraping: {test_url}\n{'─' * 50}")
    result = scrape_job_description(test_url)

    if result["success"]:
        print(f"Site detected : {result['site']}")
        print(f"Characters    : {len(result['text'])}")
        print(f"\n── First 800 chars of JD ──\n")
        print(result["text"][:800])
        print("\n...")
    else:
        print(f"Failed: {result['error']}")