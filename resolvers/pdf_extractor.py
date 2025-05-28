import io
import os
import logging
import requests
import re
import time
import tempfile
from urllib.parse import urlparse, urljoin
import subprocess

# Import PDF libraries with fallbacks
pdf_libraries = []

try:
    import pdfplumber

    pdf_libraries.append("pdfplumber")
except ImportError:
    logging.warning("pdfplumber not installed")

try:
    import fitz  # PyMuPDF

    pdf_libraries.append("pymupdf")
except ImportError:
    logging.warning("PyMuPDF not installed")

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text

    pdf_libraries.append("pdfminer")
except ImportError:
    logging.warning("pdfminer.six not installed")


def extract_with_pdfplumber(pdf_bytes):
    """Extract text using pdfplumber."""
    with io.BytesIO(pdf_bytes) as pdf_file:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n\n"
                return text
        except Exception as e:
            logging.warning(f"pdfplumber extraction failed: {e}")
            return None


def extract_with_pymupdf(pdf_bytes):
    """Extract text using PyMuPDF."""
    with io.BytesIO(pdf_bytes) as pdf_file:
        try:
            doc = fitz.open(stream=pdf_file, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e:
            logging.warning(f"PyMuPDF extraction failed: {e}")
            return None


def extract_with_pdfminer(pdf_bytes):
    """Extract text using pdfminer."""
    with io.BytesIO(pdf_bytes) as pdf_file:
        try:
            text = pdfminer_extract_text(pdf_file)
            return text
        except Exception as e:
            logging.warning(f"pdfminer extraction failed: {e}")
            return None


def extract_text_from_pdf_bytes(pdf_bytes):
    """Extract text from PDF bytes with multiple methods and enhanced OCR fallback."""
    text = ""
    extraction_methods = []

    # Try standard extractors first
    if "pdfplumber" in globals():
        extraction_methods.append(extract_with_pdfplumber)

    if "fitz" in globals():
        extraction_methods.append(extract_with_pymupdf)

    if "pdfminer" in globals():
        extraction_methods.append(extract_with_pdfminer)

    # Try each method until one works
    for method in extraction_methods:
        try:
            text = method(pdf_bytes)
            if text and len(text.strip()) > 200:  # Decent amount of text
                return text
        except Exception as e:
            logging.warning(f"PDF extraction method {method.__name__} failed: {e}")

    # If all else fails and we have OCR capability, try that
    try:
        import pytesseract
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes)
        ocr_texts = []

        for img in images:
            ocr_texts.append(pytesseract.image_to_string(img))

        return "\n".join(ocr_texts)
    except ImportError:
        logging.warning("OCR libraries not available for PDF extraction fallback")
    except Exception as e:
        logging.error(f"OCR extraction failed: {e}")

    return text


def extract_text_with_external_tools(pdf_bytes):
    """Try to extract text using external command-line tools."""
    if not pdf_bytes or len(pdf_bytes) < 1000:
        return None

    temp_dir = tempfile.mkdtemp()
    temp_input = os.path.join(temp_dir, "input.pdf")
    temp_output = os.path.join(temp_dir, "output.txt")

    try:
        # Write PDF to temp file
        with open(temp_input, "wb") as f:
            f.write(pdf_bytes)

        # Try pdftotext (poppler)
        try:
            subprocess.run(
                ["pdftotext", temp_input, temp_output],
                check=True,
                stderr=subprocess.PIPE,
            )

            with open(temp_output, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            if text and len(text.strip()) > 200:
                return text
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.warning("pdftotext command failed or not found")

        # Try pdf2txt.py (pdfminer)
        try:
            subprocess.run(
                ["pdf2txt.py", "-o", temp_output, temp_input],
                check=True,
                stderr=subprocess.PIPE,
            )

            with open(temp_output, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            if text and len(text.strip()) > 200:
                return text
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.warning("pdf2txt.py command failed or not found")

        return None
    except Exception as e:
        logging.error(f"External tool extraction failed: {e}")
        return None
    finally:
        # Clean up
        try:
            os.unlink(temp_input)
            os.unlink(temp_output)
            os.rmdir(temp_dir)
        except:
            pass


def extract_text_from_pdf_url(url, max_retries=3):
    """Extract text from a PDF URL with enhanced headers and retry mechanism."""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]

    # Use a persistent session
    session = requests.Session()

    # For AACR journals, first visit the main page to get cookies
    if "aacrjournals.org" in url:
        try:
            main_url = "https://aacrjournals.org/"
            session.get(
                main_url,
                headers={
                    "User-Agent": user_agents[0],
                    "Accept": "text/html,application/xhtml+xml,application/xml",
                    "Referer": "https://www.google.com/",
                },
            )
        except:
            pass

    for attempt in range(max_retries):
        try:
            # Use a different user agent for each attempt
            ua = user_agents[attempt % len(user_agents)]

            # Enhanced headers
            headers = {
                "User-Agent": ua,
                "Accept": "application/pdf,*/*;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }

            # Add custom headers for specific sites
            if "aacrjournals.org" in url:
                headers["Referer"] = "https://aacrjournals.org/"
                headers["Origin"] = "https://aacrjournals.org"
                headers["Cookie"] = "cookieconsent_status=dismiss"

            # Add a delay between retries with increasing backoff
            if attempt > 0:
                time.sleep(2 * attempt)

            response = session.get(url, headers=headers, stream=True, timeout=30)

            if response.status_code == 200:
                # Process PDF content
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    # PDF content found, extract text
                    pdf_bytes = response.content
                    text = extract_text_from_pdf_bytes(pdf_bytes)
                    if text and len(text.strip()) > 100:
                        return text
                else:
                    logging.warning(
                        f"Response doesn't appear to be a PDF: {content_type}"
                    )
            else:
                logging.warning(
                    f"Failed to fetch PDF, status code: {response.status_code}"
                )

        except Exception as e:
            logging.error(f"Error extracting PDF from URL {url}: {str(e)}")

    logging.error(f"Failed to extract text from PDF after {max_retries} attempts")
    return None


def extract_text_from_pdf_url_advanced(url, max_retries=3):
    """More advanced version with custom user agents and cookie handling."""
    # First try the standard method
    text = extract_text_from_pdf_url(url, max_retries)
    if text:
        return text

    # If standard method fails, try more aggressive approaches

    # Try with different user agents and headers
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]

    session = requests.Session()

    # Special handling for AACR journals
    if "aacrjournals.org" in url:
        try:
            # First visit the main site
            main_response = session.get(
                "https://aacrjournals.org/", headers={"User-Agent": user_agents[0]}
            )

            # Visit the DOI page if possible
            if "/article-pdf/doi/" in url:
                doi_part = url.split("/article-pdf/doi/")[1].split("/")[0]
                article_url = (
                    f"https://aacrjournals.org/cancerrescommun/article/doi/{doi_part}"
                )
                session.get(article_url, headers={"User-Agent": user_agents[0]})
        except:
            pass

    # Try each user agent
    for ua in user_agents:
        headers = {
            "User-Agent": ua,
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "sec-ch-ua": '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        # Add domain-specific headers
        if "aacrjournals.org" in url:
            headers["Referer"] = "https://aacrjournals.org/"
            headers["Origin"] = "https://aacrjournals.org"

        try:
            response = session.get(url, headers=headers, stream=True, timeout=30)

            if response.status_code == 200:
                pdf_bytes = response.content

                # Try to extract with standard methods
                text = extract_text_from_pdf_bytes(pdf_bytes)
                if text:
                    return text

                # If standard methods fail, try external tools
                text = extract_text_with_external_tools(pdf_bytes)
                if text:
                    return text
        except Exception as e:
            logging.warning(f"Advanced extraction with UA {ua} failed: {e}")

    return None


def download_pdf_to_temp(url, max_retries=3):
    """Download PDF to a temporary file."""
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/pdf",
            }

            if "aacrjournals.org" in url:
                headers["Referer"] = "https://aacrjournals.org/"

            response = requests.get(url, headers=headers, stream=True, timeout=30)

            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name

        except Exception as e:
            logging.error(f"Error downloading PDF: {e}")
            time.sleep(2)

    return None
