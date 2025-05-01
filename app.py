#!/usr/bin/env python3
import os
import re
import io
import csv
import json
import uuid
import time
import traceback
import requests
import pdfplumber
import xml.etree.ElementTree as ET
import logging
from urllib.parse import urlparse
from requests.exceptions import RequestException
import warnings
from collections import OrderedDict
import random
from bs4 import BeautifulSoup  # Added missing import

import ssl
import certifi

from datetime import datetime
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
    send_file,
    make_response,
)
import openai

# Initialize the OpenAI client
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")
from dotenv import load_dotenv
from Bio import Entrez
from serpapi import GoogleSearch
from utils.full_text_resolver import (
    resolve_full_text,
    extract_pmid_from_query,
    extract_doi_from_query,
    fetch_pubmed_abstract,
    fetch_fulltext_europe_pmc,
    validate_doi,
    validate_pmid,
    check_unpaywall,  # Add this import
    search_paper_by_title,  # Add this
    is_full_text,
    fetch_biorxiv_html,
    fetch_from_journal_site,
    fetch_semantic_scholar_text,
    fetch_from_open_repositories,
    extract_text_from_pdf_url,
    fetch_aacr_fulltext,
    fetch_pmc_fulltext,  # Add this import
    get_pmcid_from_pmid_or_doi,  # Add this import
    resolve_full_text_enhanced,  # This is imported
)
from utils.pdf_extractor import download_pdf_to_temp
from utils.browser_pdf_extractor import extract_pdf_with_browser, extract_aacr_html_text
from utils.institutional_access import (
    extract_text_with_institutional_access,
    try_all_institutions,
)

# Set the SSL context for the entire application
ssl._create_default_https_context = (
    ssl._create_unverified_context
)  # Not recommended for production!

# Alternatively, a more secure approach:
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ————— Init & Logging ——————————————————————————————————
load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Set API keys
# Removed unnecessary assignment
serpapi_key = os.getenv("SERPAPI_API_KEY")
Entrez.email = os.getenv("NCBI_EMAIL", "sdodl001@odu.edu")
crossref_email = os.getenv("CROSSREF_EMAIL", Entrez.email)
scopus_key = os.getenv("SCOPUS_API_KEY")
springer_key = os.getenv("SPRINGER_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
print(f"[INFO] logs directory: {LOG_DIR}")

LOG_FILE = os.path.join(LOG_DIR, "chat_logs.csv")
META_FILE = os.path.join(LOG_DIR, "metadata_log.json")


# Setup logging with a consistent format
def setup_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, "application.log")),
            logging.StreamHandler(),
        ],
    )


# Setup logging with INFO level for development
setup_logging(logging.INFO)

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

# ————— Helpers ——————————————————————————————————————————


def clean_text(t):
    return re.sub(r"\s+", " ", t or "").strip()


def clean_doi(d):
    return (
        d.lower().strip().removeprefix("https://doi.org/").removeprefix("doi:").strip()
    )


def safe_api_call(func_name, func, *args, **kwargs):
    """Wrapper for API calls with consistent error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"Error in {func_name}: {e}")
        return None


# Safe wrapper for OpenAI API calls with retries
def safe_create(**kwargs):
    """Safely create a request to OpenAI API with retries."""
    backoff = 1
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Use the client-based approach instead of the deprecated module approach
            return client.chat.completions.create(**kwargs)
        except openai.RateLimitError as e:  # Updated exception class - no more .error namespace
            retry_after = 20  # Default retry time
            if "Please try again in" in str(e):
                try:
                    retry_after = float(
                        re.search(r"try again in ([\d.]+)", str(e)).group(1)
                    )
                except:
                    pass
            logging.info(f"Rate limit hit, retrying in {retry_after:.2f} seconds...")
            time.sleep(retry_after + (random.random() * 0.5))  # Add jitter
        except Exception as e:
            logging.error(f"Error during OpenAI API call: {e}")
            raise
    raise RuntimeError("Max retries exceeded for OpenAI API call")


# Centralized model response function
def get_model_response(model, prompt):
    try:
        # For newer models that use chat completion format
        if "gpt" in model.lower():
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful scientific assistant. Answer with accurate information based on the provided paper.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )
            return response.choices[0].message.content
        # For older models that used the completion API
        else:
            response = client.completions.create(
                model=model, prompt=prompt, temperature=0.3, max_tokens=3000
            )
            return response.choices[0].text
    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        return f"Error getting response: {str(e)}"


def extract_additional_metadata(text):
    """Extract additional metadata from text."""
    gs = re.findall(r"GSE\d{5,6}", text or "")
    tr = re.findall(
        r"(Decitabine|DAC|Azacytidine|5-azacytidine)", text or "", flags=re.IGNORECASE
    )
    return {"datasets": list(set(gs)), "treatments": list(set(tr))}


def perform_search_v3(query, num_results=30, max_chars=5000):
    """Perform a search using SerpAPI."""
    sq = "site:pubmed.ncbi.nlm.nih.gov OR site:biorxiv.org OR site:nature.com " + query
    res = GoogleSearch({"q": sq, "api_key": serpapi_key, "num": num_results}).get_dict()
    out, cit, seen, chars = [], [], set(), 0
    for item in res.get("organic_results", []):
        snip = clean_text(item.get("snippet", ""))
        title, link = item.get("title", ""), item.get("link", "")
        key = (snip, title, link)
        if snip and key not in seen:
            seen.add(key)
            entry = f"Source: {title}\n{snip}\n"
            if chars + len(entry) > max_chars:
                break
            out.append(entry)
            cit.append({"title": title, "link": link})
            chars += len(entry)
    return "\n---\n".join(out), cit


def log_chat(sid, ui, reply, citations=None, paper_info=None, status=None, doi=None):
    """Log chat information to CSV file."""
    if citations is None:
        citations = []

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cit_txt = "; ".join(f"{c['title']} ({c['link']})" for c in citations)

    # Extract DOI from paper_info if available
    if paper_info and isinstance(paper_info, dict):
        doi = paper_info.get("doi", doi)

    row = [
        ts,
        sid,
        ui,
        reply,
        cit_txt,
        paper_info.get("url", "") if paper_info else "",
        status or "",
        doi or "",
    ]

    exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(
                [
                    "timestamp",
                    "session_id",
                    "user_input",
                    "model_reply",
                    "citations",
                    "pdf_url",
                    "fulltext_status",
                    "doi",
                ]
            )
        w.writerow(row)


def log_metadata(session_id, metadata):
    """Log metadata with a consistent format.

    Args:
        session_id (str): The session ID
        metadata (dict): Dictionary containing paper metadata
    """
    entry = {
        "session_id": session_id,
        "doi": metadata.get("doi"),
        "pmid": metadata.get("pmid"),
        "title": metadata.get("title"),
        "authors": metadata.get("authors"),
        "journal": metadata.get("journal"),
        "year": metadata.get("year"),
        "datasets": metadata.get("datasets", []),
        "treatments": metadata.get("treatments", []),
        "timestamp": datetime.now().isoformat(),
    }

    if not os.path.exists(META_FILE):
        with open(META_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(META_FILE, "r") as f:
            existing = json.load(f)
    except Exception as e:
        logging.error(f"Error loading metadata file: {e}")
        existing = []

    existing.append(entry)

    with open(META_FILE, "w") as f:
        json.dump(existing, f, indent=2)


# Add a global cache for storing query results with a size limit
query_cache = OrderedDict()


def add_to_cache(key, value, max_size=100):
    """Add an item to the cache with a size limit."""
    if key in query_cache:
        query_cache.pop(key)  # Remove existing entry to update order
    elif len(query_cache) >= max_size:
        query_cache.popitem(last=False)  # Remove the oldest item
    query_cache[key] = value


def list_available_models():
    """Return a list of available models across providers."""
    openai_models = [
        "gpt-4o-mini",
        "gpt-4",
        "gpt-4-32k",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    experimental_models = [
        # Add these only when they're properly implemented
        # "DeepSeek",
        # "HuggingFace-BERT",
        # "HuggingFace-GPT2"
    ]

    return openai_models + experimental_models


def fetch_plos_text(doi):
    """Fetch text for PLOS articles using their API."""
    if "plos" not in doi.lower():
        return None

    try:
        # PLOS API format
        article_id = doi.split("/")[-1]
        url = f"https://journals.plos.org/plosone/article/file?id={doi}&type=manuscript"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Extract full text
            article_text = soup.select_one("div.article-full-text")
            if article_text:
                return article_text.get_text(separator="\n")
        return None
    except Exception as e:
        logging.error(f"PLOS fetch failed: {e}")
        return None


def fetch_from_scihub(doi, enable_scihub=False):
    """Fetch PDF from SciHub (if enabled)."""
    if not enable_scihub:
        return None

    try:
        # Note: SciHub domains change frequently
        scihub_url = "https://sci-hub.se/"  # Replace with current domain
        response = requests.get(f"{scihub_url}{doi}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            iframe = soup.find("iframe")
            if iframe and iframe.get("src"):
                pdf_url = iframe.get("src")
                if pdf_url.startswith("//"):
                    pdf_url = "https:" + pdf_url
                # Then download and extract text from the PDF
                # ...
        return None
    except Exception as e:
        logging.error(f"SciHub fetch failed: {e}")
        return None


# ————— Routes ——————————————————————————————————————


@app.route("/")
def index():
    """Render the index page with a dropdown for model selection."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    models = list_available_models()
    default_model = "gpt-4o-mini"  # Set the default model
    return render_template("index.html", models=models, default_model=default_model)


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat requests with the selected model."""
    try:
        # Get user input and model selection - avoid duplicate assignments
        ui = request.form.get("message") or request.form.get("user_input", "").strip()
        selected_model = request.form.get("model", "gpt-4o-mini")
        sid = session.get("session_id", "unknown")
        ignore_cache = request.form.get("ignore_cache") == "true"

        logging.info("Processing request...")
        logging.info(f"Selected model: {selected_model}")

        # Initialize variables
        doi = None
        pmid = None
        title = None
        full_text = None
        metadata = {}
        access_status = None
        context = []  # Initialize context only once

        # Try to extract DOI or PMID from the query
        doi = extract_doi_from_query(ui)
        pmid = extract_pmid_from_query(ui)

        # If no DOI or PMID found, try to find the paper by title
        if not (doi or pmid) and len(ui or "") > 20:
            # Check if query has title indicators
            title_patterns = [
                r'titled "[^"]+"',
                r"titled: [^\.]+",
                r"publication [^\.]+",
                r"paper [^\.]+",
                r"article [^\.]+",
                r"titled (?!.*doi).*",  # Match "titled" followed by text that doesn't contain "doi"
            ]

            is_title_query = any(
                re.search(pattern, ui or "", re.IGNORECASE)
                for pattern in title_patterns
            )

            if is_title_query:
                # Extract title and search for identifiers
                for pattern in title_patterns:
                    match = re.search(pattern, ui or "", re.IGNORECASE)
                    if match:
                        potential_title = (
                            match.group(0)
                            .lower()
                            .replace("titled ", "")
                            .replace("titled: ", "")
                            .replace("publication ", "")
                            .replace("paper ", "")
                            .replace("article ", "")
                            .strip('" ')
                        )

                        if potential_title:
                            title = potential_title
                            logging.info(
                                f"Attempting to find paper with title: {potential_title}"
                            )
                            found_doi, found_pmid = search_paper_by_title(
                                potential_title
                            )

                            if found_doi or found_pmid:
                                logging.info(
                                    f"Found paper identifier - DOI: {found_doi}, PMID: {found_pmid}"
                                )
                                doi = found_doi or doi
                                pmid = found_pmid or pmid
                                break

        # Try to resolve full text if DOI or PMID is available
        if doi or pmid:
            logging.info(
                f"Attempting to resolve full text for DOI: {doi}, PMID: {pmid}"
            )
            try:
                # Use enhanced resolver
                full_text, metadata = resolve_full_text_enhanced(pmid=pmid, doi=doi, title=title)
                
                if full_text:
                    # Determine access status based on metadata
                    if metadata.get("has_full_text", False):
                        access_status = "Full Text Available"
                        # Truncate if necessary to avoid token limits
                        if len(full_text) > 10000:
                            full_text = full_text[:10000] + "...[truncated due to length]"
                        context.append(f"Full text of the paper:\n{full_text}")
                    else:
                        access_status = "Abstract Only"
                        context.append(f"Abstract of the paper:\n{full_text}")
                else:
                    access_status = "No Content Available"
            except Exception as e:
                logging.error(f"Error resolving full text: {e}")
                full_text = None
                metadata = {}
                access_status = f"Error: {str(e)}"

        # Add paper metadata to context if available
        meta_text = []
        if metadata.get("title"):
            meta_text.append(f"Title: {metadata.get('title')}")
        if metadata.get("authors"):
            meta_text.append(f"Authors: {', '.join(metadata.get('authors', []))}")
        if metadata.get("journal"):
            meta_text.append(f"Journal: {metadata.get('journal')}")
        if metadata.get("year"):
            meta_text.append(f"Year: {metadata.get('year')}")
        if metadata.get("doi"):
            meta_text.append(f"DOI: {metadata.get('doi')}")

        if meta_text:
            context.append("Paper metadata:\n" + "\n".join(meta_text))

        # Create the enhanced prompt with context if available
        if context:
            prompt = (
                f"I'd like you to analyze this scientific paper:\n\n"
                + "\n\n".join(context)
                + "\n\n"
                + f"Based on this paper, please answer the following question: {ui}"
            )
            logging.info("Using enhanced context with paper details in prompt")
        else:
            prompt = ui
            logging.info("No paper details found, using original query")

        # Get model response
        cache_key = f"{selected_model}:{prompt}"
        if not ignore_cache and cache_key in query_cache:
            reply = query_cache[cache_key]
            logging.info("Using cached response")
        else:
            reply = get_model_response(selected_model, prompt)
            add_to_cache(cache_key, reply)

        # Prepare paper info for logging and display
        paper_info = {
            "title": metadata.get("title", ""),
            "doi": metadata.get("doi", doi),
            "pmid": metadata.get("pmid", pmid),
            "url": metadata.get("pdf_url", ""),
            "has_full_text": metadata.get("has_full_text", False),
            "has_abstract": metadata.get("has_abstract", False),
            "access_status": access_status or "No paper identifiers found",
            "access_logs": metadata.get("access_logs", []),
            "source": metadata.get("source", ""),
            "text_length": metadata.get("text_length", 0),
        }

        # Log the chat information
        log_chat(sid, ui, reply, [], paper_info, status=access_status)

        # Render response
        return render_template(
            "index.html",
            models=list_available_models(),
            default_model=selected_model,
            response=reply,
            paper_info=paper_info,
        )

    except Exception as e:
        logging.error(f"Unhandled exception in chat: {str(e)}")
        error_message = f"An error occurred: {str(e)}"
        return render_template(
            "index.html",
            models=list_available_models(),
            default_model="gpt-4o-mini", 
            response=error_message,
        )


@app.route("/download_log")
def download_log():
    """Download the chat log file."""
    return (
        send_file(LOG_FILE, as_attachment=True)
        if os.path.exists(LOG_FILE)
        else "No log."
    )


@app.route("/download_metadata")
def download_metadata():
    """Download the metadata JSON file."""
    return (
        send_file(META_FILE, as_attachment=True)
        if os.path.exists(META_FILE)
        else "No metadata."
    )


@app.route("/view_metadata")
def view_metadata():
    """View metadata in HTML format."""
    if not os.path.exists(META_FILE):
        return "<h3>No metadata logged yet.</h3>"

    try:
        with open(META_FILE, "r") as f:
            entries = json.load(f)
    except Exception as e:
        return f"<h3>Error reading metadata: {e}</h3>"

    html = "<h2>Metadata Log</h2><table border=1 cellpadding=6>"
    html += "<tr><th>Timestamp</th><th>Title</th><th>DOI</th><th>PMID</th><th>Datasets</th><th>Treatments</th></tr>"

    for e in entries:
        html += f"<tr>"
        html += f"<td>{e.get('timestamp', '')}</td>"
        html += f"<td>{e.get('title', '')}</td>"
        html += f"<td>{e.get('doi', '')}</td>"
        html += f"<td>{e.get('pmid', '')}</td>"
        html += f"<td>{', '.join(e.get('datasets', []))}</td>"
        html += f"<td>{', '.join(e.get('treatments', []))}</td>"
        html += "</tr>"

    html += "</table>"
    return html


# Add this function before the test_sources route


def test_source(source_func, source_name, *args):
    """
    Test a specific source for paper content.

    Args:
        source_func: Function to call
        source_name: Name of the source for logging
        *args: Arguments to pass to the source function

    Returns:
        dict: Results of the test
    """
    results = {}
    try:
        start_time = time.time()
        text = source_func(*args)
        elapsed = time.time() - start_time

        if text:
            # Check if the text is likely full-text or just abstract
            is_full = False
            try:
                is_full = is_full_text(text)
            except Exception as e:
                logging.error(f"Error checking if text is full: {e}")

            results[source_name] = {
                "status": "success",
                "length": len(text),
                "time": f"{elapsed:.2f}s",
                "is_full_text": is_full,
            }
        else:
            results[source_name] = {
                "status": "failed",
                "message": "No content returned",
            }
    except Exception as e:
        results[source_name] = {"status": "error", "message": str(e)}
    return results


@app.route("/test_sources", methods=["GET", "POST"])
def test_sources():
    """Test and display full text access from different sources."""
    results = {}

    if request.method == "POST":
        doi = request.form.get("doi")
        pmid = request.form.get("pmid")
        title = request.form.get("title")
        pmcid = request.form.get("pmcid")

        if not (doi or pmid or title):
            return render_template(
                "test_sources.html",
                error="Please provide either DOI, PMID, or Paper Title",
            )

        # If title is provided but no DOI/PMID, try to find identifiers
        if title and not (doi or pmid):
            found_doi, found_pmid = search_paper_by_title(title)
            if found_doi or found_pmid:
                doi = found_doi
                pmid = found_pmid

        # Initialize results structure
        results = {
            "timestamp": datetime.now().isoformat(),
            "doi": doi,
            "pmid": pmid,
            "title": title,
            "sources": {},
        }

        # Use the external test_source function
        def local_test_source(source_func, source_name, *args):
            try:
                start_time = time.time()
                text = source_func(*args)
                elapsed = time.time() - start_time

                if text:
                    # Check if the text is likely full-text or just abstract
                    is_full = False
                    try:
                        is_full = is_full_text(text)
                    except Exception as e:
                        logging.error(f"Error checking if text is full: {e}")

                    results["sources"][source_name] = {
                        "status": "success",
                        "length": len(text),
                        "time": f"{elapsed:.2f}s",
                        "is_full_text": is_full,
                    }
                else:
                    results["sources"][source_name] = {
                        "status": "failed",
                        "message": "No content returned",
                    }
            except Exception as e:
                results["sources"][source_name] = {"status": "error", "message": str(e)}

        # Test PMID-based sources
        if pmid:
            local_test_source(
                lambda p: fetch_pubmed_abstract(p), "PubMed Abstract", pmid
            )
            local_test_source(
                lambda p: fetch_fulltext_europe_pmc(p), "Europe PMC", pmid
            )

            # Add PMC test
            local_test_source(
                lambda p: fetch_pmc_fulltext(pmid=p), "PubMed Central", pmid
            )

        # Test DOI-based sources
        if doi:
            local_test_source(lambda d: fetch_biorxiv_html(d), "BioRxiv", doi)
            local_test_source(lambda d: fetch_from_journal_site(d), "Journal Site", doi)
            local_test_source(
                lambda d: fetch_semantic_scholar_text(d), "Semantic Scholar", doi
            )
            local_test_source(
                lambda d: fetch_from_open_repositories(d), "Open Repositories", doi
            )

            # For AACR journals specifically
            if doi.startswith("10.1158"):
                local_test_source(lambda d: fetch_aacr_fulltext(d), "AACR Journal", doi)

            # Add PMC test for DOI too
            local_test_source(
                lambda d: fetch_pmc_fulltext(doi=d), "PubMed Central", doi
            )

            # Test Unpaywall
            if doi:
                try:
                    pdf_url = check_unpaywall(doi)
                    if pdf_url:
                        results["sources"]["Unpaywall"] = {
                            "status": "success",
                            "url": pdf_url,
                        }

                        # Try PDF extraction
                        try:
                            logging.info(f"Attempting PDF extraction from {pdf_url}")

                            # First try standard extraction
                            pdf_text = extract_text_from_pdf_url(pdf_url)
                            extraction_method = "Standard"

                            # If standard failed and it's an AACR journal, try HTML extraction
                            if not pdf_text and ("aacrjournals.org" in pdf_url):
                                # Try HTML version
                                html_text = extract_aacr_html_text(doi)
                                if html_text:
                                    pdf_text = html_text
                                    extraction_method = "HTML"

                            # Process extracted text
                            if pdf_text:
                                is_ft = (
                                    is_full_text(pdf_text)
                                    if callable(is_full_text)
                                    else len(pdf_text) > 4000
                                )
                                results["sources"]["PDF Extraction"] = {
                                    "status": "success",
                                    "length": len(pdf_text),
                                    "is_full_text": is_ft,
                                    "method": extraction_method,
                                }
                            else:
                                results["sources"]["PDF Extraction"] = {
                                    "status": "failed",
                                    "message": "All PDF extraction methods failed",
                                }
                        except Exception as e:
                            results["sources"]["PDF Extraction"] = {
                                "status": "error",
                                "message": str(e),
                            }
                    else:
                        results["sources"]["Unpaywall"] = {
                            "status": "failed",
                            "message": "No PDF URL found",
                        }
                except Exception as e:
                    results["sources"]["Unpaywall"] = {
                        "status": "error",
                        "message": str(e),
                    }

        # Direct PMCID test
        if pmcid:
            # Strip 'PMC' prefix if present
            pmcid = pmcid.replace("PMC", "")
            local_test_source(
                lambda p: fetch_pmc_fulltext(pmcid=p), "PubMed Central Direct", pmcid
            )

            # Try to get DOI and PMID from PMCID if not provided
            if not (doi or pmid):
                try:
                    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=my_tool&email={Entrez.email}&ids=PMC{pmcid}&format=json"
                    response = requests.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("records") and len(data["records"]) > 0:
                            record = data["records"][0]
                            doi = record.get("doi", doi)
                            pmid = record.get("pmid", pmid)
                except Exception as e:
                    logging.error(f"Error getting identifiers from PMCID: {e}")

        # Try the consolidated resolver
        try:
            full_text, metadata = resolve_full_text(pmid=pmid, doi=doi, title=title)
            results["consolidated"] = {
                "status": "success" if full_text else "failed",
                "text_length": len(full_text) if full_text else 0,
                "metadata": metadata,
                "is_full_text": metadata.get("has_full_text", False) if isinstance(metadata, dict) else False,
            }
        except Exception as e:
            results["consolidated"] = {"status": "error", "message": str(e)}

        # Add browser-based extraction testing for AACR journals
        if doi and doi.startswith("10.1158"):
            # First check if we have a PDF URL from Unpaywall
            pdf_url = None
            if (
                "Unpaywall" in results["sources"]
                and results["sources"]["Unpaywall"].get("status") == "success"
            ):
                pdf_url = results["sources"]["Unpaywall"].get("url")

            if pdf_url:
                try:
                    logging.info(f"Attempting browser-based extraction for {pdf_url}")
                    browser_text = extract_pdf_with_browser(pdf_url)

                    if browser_text and len(browser_text) > 200:
                        results["sources"]["Browser PDF Extraction"] = {
                            "status": "success",
                            "length": len(browser_text),
                            "is_full_text": len(browser_text)
                            > 4000,  # Simple heuristic for full text
                        }
                    else:
                        results["sources"]["Browser PDF Extraction"] = {
                            "status": "failed",
                            "message": "Browser extraction returned no text",
                        }
                except Exception as e:
                    results["sources"]["Browser PDF Extraction"] = {
                        "status": "error",
                        "message": str(e),
                    }

            # Try direct HTML approach for AACR
            try:
                html_text = extract_aacr_html_text(doi)
                if html_text and len(html_text) > 200:
                    results["sources"]["AACR HTML"] = {
                        "status": "success",
                        "length": len(html_text),
                        "is_full_text": len(html_text)
                        > 4000,  # Simple heuristic for full text
                    }
                else:
                    results["sources"]["AACR HTML"] = {
                        "status": "failed",
                        "message": "HTML extraction returned no text",
                    }
            except Exception as e:
                results["sources"]["AACR HTML"] = {"status": "error", "message": str(e)}

        # Calculate overall availability
        success_sources = [
            s
            for s, data in results["sources"].items()
            if data.get("status") == "success"
            and (s != "PubMed Abstract" or data.get("is_full_text", False))
        ]

        has_full_text = any(
            data.get("is_full_text", False) for data in results["sources"].values()
        )
        has_abstract = (
            "PubMed Abstract" in results["sources"]
            and results["sources"]["PubMed Abstract"].get("status") == "success"
        )
        has_pdf = (
            "Unpaywall" in results["sources"]
            and results["sources"]["Unpaywall"].get("status") == "success"
        )

        # Determine overall access status
        if has_full_text or (
            has_pdf
            and "PDF Extraction" in results["sources"]
            and results["sources"]["PDF Extraction"].get("status") == "success"
        ):
            access_level = "Full Text Available"
            color = "green"
        elif has_abstract:
            access_level = "Abstract Only"
            color = "orange"
        else:
            access_level = "Not Available Through Open Access"
            color = "red"

        results["overall_status"] = {
            "access_level": access_level,
            "color": color,
            "successful_sources": success_sources,
            "has_full_text": has_full_text,
            "has_abstract": has_abstract,
            "has_pdf": has_pdf,
        }

        # After your existing test cases, add institutional access testing
        if doi:
            # Import institutional access module
            from utils.institutional_access import (
                INSTITUTION_PROXIES,
                extract_text_with_institutional_access,
            )

            # Test each configured institution
            for inst_key in INSTITUTION_PROXIES.keys():
                institution_name = INSTITUTION_PROXIES[inst_key]["name"]
                source_name = f"Institutional ({institution_name})"

                local_test_source(
                    lambda d, i=inst_key: extract_text_with_institutional_access(d, i),
                    source_name,
                    doi,
                )

        # Also test the enhanced resolver
        try:
            full_text, metadata = resolve_full_text_enhanced(
                pmid=pmid, doi=doi, title=title
            )
            results["enhanced_resolver"] = {
                "status": "success" if full_text else "failed",
                "text_length": len(full_text) if full_text else 0,
                "metadata": metadata,
                "is_full_text": metadata.get("has_full_text", False),
                "source": metadata.get("source", "Unknown"),
            }
        except Exception as e:
            results["enhanced_resolver"] = {"status": "error", "message": str(e)}

    return render_template("test_sources.html", results=results)


if __name__ == "__main__":
    # Configure logging only for the main process
    setup_logging(logging.WARNING)  # Use WARNING level for production

    print(f"[INFO] logs directory: {LOG_DIR}")
    logging.info("Starting the application...")
    app.run(debug=False, host="0.0.0.0", port=8000)
