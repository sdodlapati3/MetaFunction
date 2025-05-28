import os
import time
import tempfile
import logging
import requests
import io
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import subprocess
from bs4 import BeautifulSoup

# Reuse your existing PDF extraction methods
from utils.pdf_extractor import extract_text_from_pdf_bytes

# Configure logging
logging.basicConfig(level=logging.INFO)


def extract_pdf_with_browser(url, timeout=60):
    """
    Extract text from PDF using browser automation.

    Args:
        url: URL of the PDF
        timeout: Maximum time to wait in seconds

    Returns:
        str: Extracted text or None if extraction failed
    """
    logging.info(f"Starting browser-based PDF extraction for {url}")

    # Create temporary directory for downloads
    temp_dir = tempfile.mkdtemp()
    logging.info(f"Created temporary directory at {temp_dir}")

    try:
        # Check if Selenium is installed
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logging.error("Selenium not installed. Install with: pip install selenium")
            return None

        # Try to use webdriver-manager for ChromeDriver installation
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            chromedriver_path = ChromeDriverManager().install()
        except ImportError:
            logging.warning(
                "webdriver-manager not installed, using system ChromeDriver"
            )
            chromedriver_path = None

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Add user agent to appear as a real browser
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
        )

        # Configure download settings
        prefs = {
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "pdfjs.disabled": True,  # Disable built-in PDF viewer
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Initialize Chrome driver
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

        logging.info("Chrome WebDriver initialized")

        try:
            # Handle specific domains with special procedures
            domain = urlparse(url).netloc.lower()

            if "aacrjournals.org" in domain:
                return _handle_aacr_journals(driver, url, temp_dir, timeout)
            else:
                return _generic_pdf_extraction(driver, url, temp_dir, timeout)

        finally:
            driver.quit()
            logging.info("WebDriver closed")

    except Exception as e:
        logging.error(f"Browser PDF extraction error: {str(e)}")
        return None
    finally:
        # Cleanup temp directory
        try:
            import shutil

            shutil.rmtree(temp_dir)
            logging.info(f"Removed temporary directory {temp_dir}")
        except Exception as e:
            logging.error(f"Failed to remove temp directory: {str(e)}")


def _handle_aacr_journals(driver, url, temp_dir, timeout):
    """Special handler for AACR journals with enhanced methods."""
    logging.info("Using AACR-specific extraction procedure")

    # First navigate to the AACR homepage to get cookies
    driver.get("https://aacrjournals.org/")
    time.sleep(3)  # Extra wait time

    # Add cookies that might help with access
    driver.add_cookie({"name": "cookieconsent_status", "value": "dismiss"})
    driver.add_cookie({"name": "gdpr", "value": "true"})

    # Extract DOI from URL if possible
    doi = None
    if "/doi/" in url:
        try:
            doi_part = url.split("/doi/")[1].split("/")[0]
            if "10.1158" in doi_part:
                doi = doi_part
        except:
            pass

    # IMPORTANT: Try multiple access patterns
    article_patterns = []

    # Standard DOI-based article URL
    if doi:
        article_patterns = [
            f"https://aacrjournals.org/cancerrescommun/article/doi/{doi}/729101/Epigenetic-Induction-of-Cancer-Testis-Antigens-and",
            f"https://aacrjournals.org/cancerrescommun/article/doi/{doi}",
            # New: Try the abstract page first (often less protected)
            f"https://aacrjournals.org/cancerrescommun/article-abstract/doi/{doi}",
            # Try alternate pattern used by some AACR journals
            f"https://aacrjournals.org/cancerres/article/doi/{doi}",
        ]

    # Try article pages first (HTML is less restrictive than PDF)
    for article_url in article_patterns:
        try:
            logging.info(f"Trying AACR article URL: {article_url}")
            driver.get(article_url)
            time.sleep(5)

            # Check if we've got the article
            for selector in [
                "div.article-body",
                "section.article__sections",
                "div.hlFld-Fulltext",
                "section.article__abstract",
                "div#content-block",
                "section.abstract",
            ]:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        text = "\n\n".join(
                            [elem.text for elem in elements if elem.text.strip()]
                        )
                        if text and len(text) > 500:
                            logging.info(
                                f"Successfully extracted HTML text from AACR article via {selector}"
                            )
                            return text
                except Exception as e:
                    logging.warning(f"Error with selector {selector}: {e}")
        except Exception as e:
            logging.warning(f"Error accessing {article_url}: {e}")

    # New technique: Try to find and click PDF link on article page
    if doi:
        try:
            article_url = f"https://aacrjournals.org/cancerrescommun/article/doi/{doi}"
            driver.get(article_url)
            time.sleep(3)

            # Look for PDF links using various patterns
            pdf_link_xpaths = [
                "//a[contains(@href, 'article-pdf')]",
                "//a[contains(text(), 'PDF')]",
                "//a[contains(@class, 'pdf-link')]",
                "//a[contains(@title, 'PDF')]",
            ]

            for xpath in pdf_link_xpaths:
                try:
                    links = driver.find_elements(By.XPATH, xpath)
                    if links:
                        links[0].click()
                        logging.info(f"Clicked PDF link found with {xpath}")
                        time.sleep(10)  # Wait for possible download

                        # Check for downloads
                        files = os.listdir(temp_dir)
                        pdf_files = [f for f in files if f.endswith(".pdf")]
                        if pdf_files:
                            pdf_path = os.path.join(temp_dir, pdf_files[0])
                            logging.info(f"Found downloaded PDF: {pdf_path}")
                            return _extract_text_from_downloaded_pdf(pdf_path)
                except Exception as e:
                    logging.warning(f"Error with PDF link {xpath}: {e}")
        except Exception as e:
            logging.warning(f"Error accessing article for PDF link: {e}")

    # If all else fails, try our last resort PDF URL directly
    logging.info(f"Trying direct PDF URL as last resort: {url}")
    driver.get(url)
    time.sleep(10)  # Extra wait time for PDF

    # Check for downloads
    files = os.listdir(temp_dir)
    pdf_files = [f for f in files if f.endswith(".pdf")]
    if pdf_files:
        pdf_path = os.path.join(temp_dir, pdf_files[0])
        logging.info(f"Found downloaded PDF: {pdf_path}")
        return _extract_text_from_downloaded_pdf(pdf_path)

    logging.warning("All AACR extraction methods failed")
    return None


def _generic_pdf_extraction(driver, url, temp_dir, timeout):
    """Generic PDF extraction procedure for most sites."""
    logging.info(f"Navigating to PDF URL: {url}")
    driver.get(url)

    # Wait for possible download to complete
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for downloaded files
        files = os.listdir(temp_dir)
        pdf_files = [f for f in files if f.endswith(".pdf")]

        if pdf_files:
            pdf_path = os.path.join(temp_dir, pdf_files[0])
            logging.info(f"Found downloaded PDF: {pdf_path}")

            # Extract text using external tools
            return _extract_text_from_downloaded_pdf(pdf_path)

        # If no download yet, wait a bit
        time.sleep(2)

    # If we reached here, no PDF was downloaded
    logging.warning("No PDF was downloaded within the timeout period")
    return None


def _extract_text_from_downloaded_pdf(pdf_path):
    """Extract text from a downloaded PDF file using available tools."""
    logging.info(f"Extracting text from PDF: {pdf_path}")

    # Try importing PDF extraction libraries
    try:
        from utils.pdf_extractor import extract_text_from_pdf_bytes

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        text = extract_text_from_pdf_bytes(pdf_bytes)
        if text and len(text) > 200:
            logging.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
    except ImportError:
        logging.warning("PDF extractor module not available")
    except Exception as e:
        logging.error(f"Error using PDF extractor: {e}")

    # If the import fails or extraction fails, try external tools

    # Try pdftotext (from poppler-utils)
    try:
        output = subprocess.check_output(
            ["pdftotext", pdf_path, "-"], stderr=subprocess.PIPE
        )
        text = output.decode("utf-8", errors="ignore")
        if text and len(text) > 200:
            logging.info(
                f"Successfully extracted {len(text)} characters using pdftotext"
            )
            return text
    except (subprocess.SubprocessError, FileNotFoundError):
        logging.warning("pdftotext not available or failed")

    # Try OCR as a last resort
    try:
        import pytesseract
        from pdf2image import convert_from_path

        logging.info("Attempting OCR extraction...")
        pages = convert_from_path(pdf_path, 300)
        text_parts = []

        for i, page in enumerate(pages):
            logging.info(f"OCR processing page {i+1} of {len(pages)}")
            text = pytesseract.image_to_string(page)
            text_parts.append(text)

        text = "\n\n".join(text_parts)
        if text and len(text) > 200:
            logging.info(f"Successfully extracted {len(text)} characters using OCR")
            return text
        else:
            logging.warning("OCR extraction yielded insufficient text")
    except ImportError:
        logging.warning("OCR libraries not available")
    except Exception as e:
        logging.error(f"OCR extraction error: {e}")

    return None


# Replace the external service function with this improved version


def extract_pdf_with_external_service(url):
    """
    Placeholder for PDF extraction using external services.
    In a production system, this would connect to a real service.
    """
    logging.warning("External PDF service is not configured")

    # For demonstration purposes only
    try:
        import tempfile
        import os

        # Download the PDF to a temporary file
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

        if response.status_code != 200:
            return None

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp_path = temp.name
            temp.write(response.content)

        # In a real implementation, you would call an external API here
        # For now, we'll just return a placeholder message

        # Clean up the temp file
        try:
            os.unlink(temp_path)
        except:
            pass

        return None
    except Exception as e:
        logging.error(f"External PDF service extraction failed: {e}")
        return None


# Enhance the AACR HTML extraction function


def extract_aacr_html_text(doi):
    """Extract text directly from AACR HTML article pages with enhanced methods."""
    if not doi or not doi.startswith("10.1158"):
        return None

    try:
        # Create multiple possible URL patterns
        journal_codes = [
            "cancerrescommun",
            "cancerres",
            "clincancerres",
            "bloodcancerdiscov",
        ]

        urls = []
        # Try multiple journal codes since papers can appear in different journals
        for journal_code in journal_codes:
            urls.extend(
                [
                    f"https://aacrjournals.org/{journal_code}/article/doi/{doi}",
                    f"https://aacrjournals.org/{journal_code}/article-abstract/doi/{doi}",
                    # More likely to succeed than PDF
                    f"https://aacrjournals.org/{journal_code}/article-standard/doi/{doi}",
                ]
            )

        session = requests.Session()

        # First get cookies from main site with enhanced headers
        session.get(
            "https://aacrjournals.org/",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Cache-Control": "no-cache",
            },
        )

        # Set cookies that might help with access
        session.cookies.set("cookieconsent_status", "dismiss")
        session.cookies.set("gdpr", "true")

        # Try broader range of selectors and URL patterns
        for url in urls:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    "Accept": "text/html,application/xhtml+xml",
                    "Referer": "https://aacrjournals.org/",
                    "Origin": "https://aacrjournals.org",
                }

                logging.info(f"Trying AACR URL: {url}")
                response = session.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Try multiple selectors for article content
                    for selector in [
                        "div.article-body",
                        "section.article__abstract",
                        "div.hlFld-Fulltext",
                        "main article",
                        "div#content-block",
                        "section.article__section__content",
                        # Add more specific AACR selectors
                        "div.abstract-view",
                        "section#section-abstract",
                        "section.abstract",
                    ]:
                        content = soup.select(selector)
                        if content:
                            text = "\n\n".join(
                                [
                                    elem.get_text(separator="\n", strip=True)
                                    for elem in content
                                ]
                            )
                            if (
                                text and len(text) > 200
                            ):  # Lower threshold to catch abstracts
                                logging.info(
                                    f"Successfully extracted AACR HTML content from {url} using {selector}"
                                )
                                return text

                    # If we got here, we didn't find content with our selectors
                    # Check for paywalled content indicators and log them
                    paywall_indicators = [
                        "paywall",
                        "purchase",
                        "subscribe",
                        "access-message",
                    ]
                    for indicator in paywall_indicators:
                        if soup.find(text=re.compile(indicator, re.I)):
                            logging.info(
                                f"Found paywall indicator '{indicator}' on page"
                            )

                # Log all links in the page for debugging
                links = soup.find_all("a", href=True)
                pdf_links = [
                    link["href"] for link in links if "pdf" in link["href"].lower()
                ]
                if pdf_links:
                    logging.info(
                        f"Found {len(pdf_links)} potential PDF links on page: {pdf_links[:3]}"
                    )

                    # Try to follow the first PDF link
                    for pdf_link in pdf_links[:2]:  # Try top 2 links
                        try:
                            abs_pdf_link = (
                                pdf_link
                                if pdf_link.startswith("http")
                                else f"https://aacrjournals.org{pdf_link}"
                            )
                            pdf_response = session.get(
                                abs_pdf_link, headers=headers, timeout=30
                            )
                            if (
                                pdf_response.status_code == 200
                                and pdf_response.headers.get("Content-Type", "").lower()
                                == "application/pdf"
                            ):
                                from utils.pdf_extractor import (
                                    extract_text_from_pdf_bytes,
                                )

                                pdf_text = extract_text_from_pdf_bytes(
                                    pdf_response.content
                                )
                                if pdf_text:
                                    logging.info(
                                        f"Successfully extracted text from PDF link: {abs_pdf_link}"
                                    )
                                    return pdf_text
                        except Exception as e:
                            logging.warning(f"Error following PDF link {pdf_link}: {e}")

            except Exception as e:
                logging.warning(f"Error accessing AACR URL {url}: {str(e)}")
                continue

        return None
    except Exception as e:
        logging.error(f"AACR HTML extraction error: {str(e)}")
        return None
