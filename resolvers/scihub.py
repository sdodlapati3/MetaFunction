import requests
import logging
from bs4 import BeautifulSoup
import re
import time
import random
from utils.pdf_extractor import (
    extract_text_from_pdf_bytes,
    extract_text_with_external_tools,
)


def fetch_from_scihub(doi):
    """
    Fetch paper from SciHub.
    Note: Use this function only where legal and in compliance with your local laws.
    """
    # SciHub domains change frequently, update these as needed
    domains = ["https://sci-hub.se", "https://sci-hub.st", "https://sci-hub.ru"]

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    ]

    # Clean DOI
    doi = doi.strip()
    if doi.startswith("http"):
        doi = re.sub(r"^https?://doi.org/", "", doi)

    # Try each domain
    random.shuffle(domains)  # Randomize to distribute load

    for domain in domains:
        try:
            ua = random.choice(user_agents)
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            }

            # First try the DOI search page
            url = f"{domain}/{doi}"
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logging.warning(
                    f"SciHub {domain} returned status code {response.status_code}"
                )
                continue

            # Parse the response
            soup = BeautifulSoup(response.text, "html.parser")

            # Check for PDF iframe
            iframe = soup.select_one("#pdf")
            if iframe and "src" in iframe.attrs:
                pdf_url = iframe["src"]
                if pdf_url.startswith("//"):
                    pdf_url = f"https:{pdf_url}"
                elif not pdf_url.startswith("http"):
                    pdf_url = urljoin(domain, pdf_url)

                # Download PDF
                pdf_response = requests.get(pdf_url, headers=headers, timeout=30)
                if pdf_response.status_code == 200:
                    # Try to extract text
                    pdf_content = pdf_response.content
                    text = extract_text_from_pdf_bytes(pdf_content)

                    if not text:
                        text = extract_text_with_external_tools(pdf_content)

                    if text:
                        return text

            # If no iframe, check for embedded PDF
            pdf_buttons = soup.select("button#save")
            if pdf_buttons:
                # This means PDF is embedded, try to get its data
                # (Implementation would depend on how SciHub structures its embedded PDFs)
                pass

            # Last resort: check for download links
            download_links = soup.select('a[href$=".pdf"]')
            if download_links:
                for link in download_links:
                    pdf_url = link["href"]
                    if pdf_url.startswith("//"):
                        pdf_url = f"https:{pdf_url}"
                    elif not pdf_url.startswith("http"):
                        pdf_url = urljoin(domain, pdf_url)

                    # Download PDF
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=30)
                    if pdf_response.status_code == 200:
                        # Try to extract text
                        text = extract_text_from_pdf_bytes(pdf_response.content)
                        if text:
                            return text

        except Exception as e:
            logging.error(f"Error accessing SciHub {domain}: {e}")

        # Wait before trying next domain
        time.sleep(1)

    return None
