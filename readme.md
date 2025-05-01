# MetaFunction

MetaFunction is an AI-powered research assistant that helps scientists access, analyze, and interact with scientific papers. It combines advanced full-text retrieval capabilities with large language models to make scientific literature more accessible and actionable.

![MetaFunction Logo](https://github.com/yourusername/MetaFunction/raw/main/static/logo.png)

## Features

- **Automatic Paper Identification**: Recognizes DOIs, PMIDs, or paper titles in natural language queries
- **Multi-Source Full Text Access**: Retrieves papers from 15+ sources including:
  - PubMed Central
  - Europe PMC
  - Journal publisher websites
  - BioRxiv/MedRxiv
  - Semantic Scholar
  - Open access repositories
  - Institutional access systems
- **Advanced PDF Processing**: Multiple methods to extract text from PDFs
- **AI-Powered Analysis**: Uses OpenAI models to analyze papers and answer specific research questions
- **Source Testing Tool**: Built-in diagnostics to evaluate paper accessibility from different sources
- **Institutional Access Integration**: Support for authenticated institutional access to subscription content

## Installation

### Prerequisites

- Python 3.8+
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/MetaFunction.git
cd MetaFunction

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
touch .env
```

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key
SERPAPI_API_KEY=your_serpapi_key
NCBI_EMAIL=your_email@example.com
CROSSREF_EMAIL=your_email@example.com

# Optional API keys
SCOPUS_API_KEY=your_scopus_key
SPRINGER_API_KEY=your_springer_key
```

## Usage

### Starting the Application

Run the Flask app:

```bash
python app.py
```

The web interface will be accessible at:  
**http://localhost:8000**

### Querying Papers

Enter a question about a scientific paper in the input field. You can:
- Include a DOI:  
  `"What are the main findings of the paper with DOI: 10.1158/2767-9764.CRC-23-0566?"`
- Include a PMID:  
  `"Summarize the paper with PMID 38856710"`
- Reference by title:  
  `"What methods were used in the paper titled 'Epigenetic Induction of Cancer-Testis Antigens'?"`

Select an AI model from the dropdown and submit your query.

### Testing Paper Access

MetaFunction includes a diagnostic tool to test paper accessibility:

- Navigate to: **http://localhost:8000/test_sources**
- Enter a DOI, PMID, or paper title
- Click "Test Sources"
- The system will attempt to retrieve the paper from all configured sources and display results

## Architecture

MetaFunction consists of several components:

- **Flask Web Application**: Handles user interface and requests
- **Full Text Resolver**: Resolves paper identifiers and retrieves content
- **PDF Extractors**: Multiple methods to process PDF files
- **Browser-Based Extraction**: Uses browser automation for challenging sites
- **Institutional Access**: Integration with institutional subscriptions
- **AI Models**: Integration with OpenAI GPT models

## Developer Notes

### Project Structure

```
MetaFunction/
├── app.py                    # Main Flask application
├── utils/
│   ├── full_text_resolver.py      # Paper retrieval logic
│   ├── pdf_extractor.py           # PDF processing
│   ├── browser_pdf_extractor.py   # Browser-based extraction
│   └── institutional_access.py    # Institutional access
├── templates/               # Flask HTML templates
├── static/                  # Static assets
└── logs/                    # Application logs
```

### Adding New Sources

To add support for a new publication source:
- Update the `PUBLISHER_REGISTRY` in `full_text_resolver.py`
- Implement any specialized extraction logic if needed
- Add testing logic in the `/test_sources` route in `app.py`

### Institutional Access

To configure institutional access:
- Update the `INSTITUTION_PROXIES` dictionary in `institutional_access.py`
- Add your institution's EZproxy URL and credentials if needed

### Logging and Monitoring

MetaFunction maintains comprehensive logs:
- `application.log`: Runtime logs
- `chat_logs.csv`: User query and response logs
- `metadata_log.json`: Retrieved paper metadata

Access logs via web interface:
- `/download_log`: Download chat history
- `/download_metadata`: Download paper metadata
- `/view_metadata`: View paper metadata in HTML format

## License

MIT License

## Acknowledgments

- **OpenAI** for providing the GPT API for scientific paper analysis
- **PubMed Central** and **Europe PMC** for open access to biomedical literature
- The **open science movement** for promoting freely accessible research

> **Note**: This project is for research and educational purposes only. Users are responsible for complying with publisher terms of service and copyright laws.
