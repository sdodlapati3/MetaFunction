import os
import time
import logging
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO)

# Dictionary of institutions and their proxy URLs
INSTITUTION_PROXIES = {
    "odu": {
        "name": "Old Dominion University",
        "proxy_url": "https://login.proxy.lib.odu.edu/login?url=",
        "login_selectors": {
            "username": "#username",
            "password": "#password",
            "submit": "input[name='submit']",
        },
    },
    "gatech": {
        "name": "Georgia Tech",
        "proxy_url": "https://login.gatech.edu/cas/login?service=",
        "login_selectors": {
            "username": "#username",
            "password": "#password",
            "submit": "input[name='submit']",
        },
    },
    "mit": {
        "name": "MIT",
        "proxy_url": "https://libproxy.mit.edu/login?url=",
        "login_selectors": {
            "username": "#username",
            "password": "#password",
            "submit": "input[name='submit']",
        },
    },
    # Add more institutions as needed
}


def get_institutional_credentials():
    """Get institutional credentials from environment variables."""
    return {
        "odu": {
            "username": os.getenv("ODU_USERNAME"),
            "password": os.getenv("ODU_PASSWORD"),
        },
        "gatech": {
            "username": os.getenv("GATECH_USERNAME"),
            "password": os.getenv("GATECH_PASSWORD"),
        },
        "mit": {
            "username": os.getenv("MIT_USERNAME"),
            "password": os.getenv("MIT_PASSWORD"),
        },
        # Add more institutions as needed
    }


def build_proxy_url(doi, institution_key):
    """Build proxy URL for a given DOI and institution."""
    if institution_key not in INSTITUTION_PROXIES:
        return None

    base_url = f"https://doi.org/{doi}"
    proxy_prefix = INSTITUTION_PROXIES[institution_key]["proxy_url"]
    return f"{proxy_prefix}{quote(base_url)}"


def extract_text_with_institutional_access(doi, institution_key="odu"):
    """
    Extract full text using institutional access.

    Args:
        doi (str): DOI of the paper
        institution_key (str): Key for the institution to use

    Returns:
        str: Extracted text or None if extraction failed
    """
    if institution_key not in INSTITUTION_PROXIES:
        logging.error(f"Institution {institution_key} not found in configuration")
        return None

    credentials = get_institutional_credentials().get(institution_key)
    if (
        not credentials
        or not credentials.get("username")
        or not credentials.get("password")
    ):
        logging.error(f"No valid credentials found for {institution_key}")
        return None

    proxy_url = build_proxy_url(doi, institution_key)
    if not proxy_url:
        return None

    logging.info(
        f"Attempting to access {doi} via {INSTITUTION_PROXIES[institution_key]['name']}"
    )

    # Initialize headless browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )

    try:
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to proxy URL
        driver.get(proxy_url)
        time.sleep(3)  # Allow page to load

        # Check if login is required
        selectors = INSTITUTION_PROXIES[institution_key]["login_selectors"]
        try:
            # Wait for username field to appear
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors["username"]))
            )

            # Fill in credentials
            username_field.send_keys(credentials["username"])
            password_field = driver.find_element(By.CSS_SELECTOR, selectors["password"])
            password_field.send_keys(credentials["password"])
            submit_button = driver.find_element(By.CSS_SELECTOR, selectors["submit"])
            submit_button.click()

            # Wait for redirect after login
            time.sleep(5)

        except TimeoutException:
            # No login form found, may be already logged in or no auth needed
            logging.info("No login form detected, proceeding")

        # Now we should be on the article page
        # Wait for content to load
        time.sleep(5)

        # Detect common article content selectors
        content_selectors = [
            "article",
            "div.article-body",
            "div.fulltext",
            "section.body",
            "div#content-block",
            "div.content-main",
            "div.article__content",
            "div#full-text-section",
        ]

        # Try to find content
        for selector in content_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                text = "\n\n".join(
                    [elem.text for elem in elements if elem.text.strip()]
                )
                if text and len(text) > 500:  # Reasonable minimum for article content
                    logging.info(
                        f"Successfully extracted content via {institution_key} proxy"
                    )
                    return text

        # If content not found with selectors, get all page text as fallback
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if len(body_text) > 1000:  # Higher threshold for full page text
            logging.info(f"Extracted full page content via {institution_key} proxy")
            return body_text

        # Check for PDF links as a last resort
        pdf_link_selectors = [
            "a[href$='.pdf']",
            "//a[contains(text(), 'PDF')]",  # Corrected XPath
            "//a[contains(text(), 'Full Text')]",  # Corrected XPath
            "a.pdf-link",
        ]

        for selector in pdf_link_selectors:
            try:
                pdf_links = driver.find_elements(By.CSS_SELECTOR, selector)
                if pdf_links:
                    # Click the first PDF link
                    pdf_links[0].click()
                    time.sleep(5)  # Wait for PDF to load or download

                    # Current URL might now be PDF
                    if driver.current_url.endswith(".pdf"):
                        from utils.pdf_extractor import extract_text_from_pdf_url

                        return extract_text_from_pdf_url(driver.current_url)
            except Exception as e:
                logging.error(f"Error trying to access PDF: {e}")

        logging.warning(f"Could not extract content via {institution_key} proxy")
        return None

    except Exception as e:
        logging.error(f"Error during institutional access via {institution_key}: {e}")
        return None
    finally:
        try:
            driver.quit()
        except:
            pass


def try_all_institutions(doi):
    """Try accessing the paper through all configured institutions."""
    for institution in INSTITUTION_PROXIES.keys():
        text = extract_text_with_institutional_access(doi, institution)
        if text:
            return text, institution
    return None, None
