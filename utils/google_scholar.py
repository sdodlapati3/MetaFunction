import requests
import logging
from bs4 import BeautifulSoup
import urllib.parse
import time
import random


def search_google_scholar(title, max_results=5):
    """Search Google Scholar for a paper title and return potential links."""
    query = urllib.parse.quote(title)
    url = f"https://scholar.google.com/scholar?q={query}&hl=en"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    results = []
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.warning(
                f"Google Scholar returned status code: {response.status_code}"
            )
            return results

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(".gs_ri")

        for article in articles[:max_results]:
            title_elem = article.select_one(".gs_rt")
            link_elem = title_elem.find("a") if title_elem else None
            link = link_elem["href"] if link_elem else None

            if not link:
                continue

            # Check for PDF links
            all_links = article.select("a")
            pdf_link = None
            for a in all_links:
                if a.text == "[PDF]":
                    pdf_link = a["href"]
                    break

            results.append(
                {
                    "title": title_elem.get_text() if title_elem else "Unknown",
                    "link": link,
                    "pdf_link": pdf_link,
                }
            )

        return results
    except Exception as e:
        logging.error(f"Error searching Google Scholar: {e}")
        return results


def get_fulltext_via_google_scholar(title, doi=None):
    """Try to get fulltext via Google Scholar bypassing paywalls."""
    logging.info(f"Searching Google Scholar for: {title}")

    # Add DOI to search if available
    search_query = title
    if doi:
        search_query += f" {doi}"

    results = search_google_scholar(search_query)
    if not results:
        return None

    # Try PDF links first
    pdf_results = [r for r in results if r.get("pdf_link")]
    for result in pdf_results:
        try:
            pdf_link = result["pdf_link"]
            logging.info(f"Trying PDF link from Google Scholar: {pdf_link}")

            # Check if it's an institutional repository or known open access site
            is_likely_open = any(
                domain in pdf_link.lower()
                for domain in [
                    "researchgate",
                    "arxiv",
                    "biorxiv",
                    "ncbi.nlm.nih.gov",
                    "europepmc.org",
                    ".edu/",
                    ".ac.",
                    "repository.",
                    "zenodo",
                    "osf.io",
                    "figshare",
                    "preprints",
                ]
            )

            if is_likely_open:
                # Try to extract text from the PDF
                from utils.pdf_extractor import extract_text_from_pdf_url

                pdf_text = extract_text_from_pdf_url(pdf_link)
                if pdf_text and len(pdf_text) > 1000:
                    logging.info(
                        f"Successfully extracted {len(pdf_text)} characters from Google Scholar PDF"
                    )
                    return pdf_text

            # If extraction failed, try browser method
            try:
                from utils.browser_pdf_extractor import extract_pdf_with_browser

                browser_text = extract_pdf_with_browser(pdf_link)
                if browser_text and len(browser_text) > 1000:
                    logging.info(
                        f"Successfully extracted {len(browser_text)} characters via browser"
                    )
                    return browser_text
            except Exception as e:
                logging.warning(f"Browser PDF extraction failed: {e}")

        except Exception as e:
            logging.warning(f"Error processing Google Scholar PDF: {e}")

    # If PDF extraction failed, try HTML links
    for result in results:
        try:
            link = result["link"]
            logging.info(f"Trying HTML link from Google Scholar: {link}")

            # Check if it's a publisher site or institutional page
            is_publisher = any(
                domain in link.lower()
                for domain in [
                    "sciencedirect",
                    "springer",
                    "wiley",
                    "tandfonline",
                    "sagepub",
                    "aacrjournals",
                    "nature",
                    "science",
                    "cell.com",
                    "ojs.",
                ]
            )

            # Use enhanced session with multiple user agents
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
            }

            session = requests.Session()
            response = session.get(link, headers=headers, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Try to find article content using common selectors
                selectors = [
                    "div.article-body",
                    "div.fulltext",
                    "article",
                    "main .content",
                    "div#content-block",
                    "div.article__content",
                    "section.abstract",
                ]

                for selector in selectors:
                    content = soup.select(selector)
                    if content:
                        text = "\n\n".join(
                            [
                                elem.get_text(separator="\n", strip=True)
                                for elem in content
                            ]
                        )
                        if text and len(text) > 500:
                            logging.info(
                                f"Successfully extracted {len(text)} characters from HTML via Google Scholar"
                            )
                            return text
        except Exception as e:
            logging.warning(f"Error processing Google Scholar HTML link: {e}")

    return None
