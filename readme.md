# 🧬 MetaFunction

<div align="center">

**AI-Powered Scientific Paper Analysis & Summarization Platform**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://black.readthedocs.io/)

*Transform scientific literature into actionable insights with cutting-edge AI*

[🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🔧 API Reference](#-api-reference) • [🤝 Contributing](#-contributing)

</div>

---

## ✨ Overview

MetaFunction is a sophisticated Flask-based platform that revolutionizes how researchers interact with scientific literature. By combining advanced paper resolution capabilities with multiple AI backends, it provides intelligent summarization and analysis of academic papers through simple queries.

### 🎯 Key Features

- **🔍 Multi-Modal Paper Resolution**: Search by DOI, PMID, arXiv ID, or paper title
- **🤖 AI-Powered Analysis**: Integration with OpenAI, DeepSeek, and Perplexity models
- **📄 Full-Text Extraction**: Advanced PDF processing and institutional access
- **🌐 Web Interface**: Clean, responsive UI for researchers
- **🔧 REST API**: Programmatic access for automation and integration
- **📊 Comprehensive Logging**: Detailed analytics and usage tracking
- **🏗️ Modular Architecture**: Clean separation of concerns for maintainability

## 🏛️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │    REST API     │    │   AI Services   │
│                 │    │                 │    │                 │
│  • Flask Routes │◄──►│  • Endpoints    │◄──►│  • OpenAI       │
│  • Templates    │    │  • Validation   │    │  • DeepSeek     │
│  • Static Assets│    │  • Serialization│    │  • Perplexity   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Services Layer                        │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐      │
│  │ Paper Service │  │  AI Service   │  │Logging Service│      │
│  │               │  │               │  │               │      │
│  │• Resolution   │  │• Model Mgmt   │  │• Structured   │      │
│  │• Validation   │  │• API Clients  │  │• Analytics    │      │
│  │• Caching      │  │• Load Balance │  │• Monitoring   │      │
│  └───────────────┘  └───────────────┘  └───────────────┘      │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Resolution Layer                             │
│                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │   PubMed     │ │    DOI       │ │ Institutional│ │ SciHub ││
│  │   Resolver   │ │   Resolver   │ │   Access     │ │Resolver││
│  │              │ │              │ │              │ │        ││
│  │• PMC Access  │ │• CrossRef    │ │• Proxy Support│ │• Backup││
│  │• Metadata    │ │• Publisher   │ │• Multi-Inst   │ │• Ethics││
│  │• Full-text   │ │• Standards   │ │• Auth Methods │ │• Limits││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
MetaFunction/
├── 🏗️  Core Application
│   ├── app/                           # Main application package
│   │   ├── __init__.py               # Package initialization
│   │   ├── main.py                   # Flask app factory
│   │   ├── config.py                 # Environment configuration
│   │   ├── clients/                  # AI API clients
│   │   │   ├── base_client.py        # Base client interface
│   │   │   ├── openai_client.py      # OpenAI integration
│   │   │   ├── deepseek_client.py    # DeepSeek integration
│   │   │   └── perplexity_client.py  # Perplexity integration
│   │   ├── routes/                   # Request handlers
│   │   │   ├── web.py               # Web interface routes
│   │   │   └── api.py               # REST API endpoints
│   │   ├── services/                 # Business logic
│   │   │   ├── ai_service.py        # AI model orchestration
│   │   │   ├── paper_service.py     # Paper resolution logic
│   │   │   └── logging_service.py   # Structured logging
│   │   └── utils/                    # Shared utilities
│   │       ├── exceptions.py        # Custom exception classes
│   │       └── validators.py        # Input validation
│   │
├── 🔍 Paper Resolution
│   ├── resolvers/                    # Paper content resolution
│   │   ├── full_text_resolver.py    # Main resolution orchestrator
│   │   ├── pdf_extractor.py         # PDF text extraction
│   │   ├── institutional_access.py  # Institutional proxy access
│   │   ├── browser_pdf_extractor.py # Browser-based extraction
│   │   ├── google_scholar.py        # Google Scholar integration
│   │   └── scihub.py               # SciHub access (ethical use)
│   │
├── 🌐 User Interface
│   ├── templates/                    # Jinja2 templates
│   │   ├── index.html               # Main interface
│   │   ├── test_sources.html        # Source testing
│   │   ├── admin/                   # Admin interface
│   │   └── components/              # Reusable components
│   ├── static/                       # Static assets
│   │   ├── css/                     # Stylesheets
│   │   ├── js/                      # JavaScript
│   │   └── images/                  # Images and icons
│   │
├── 🧪 Testing & Development
│   ├── tests/                        # Comprehensive test suite
│   │   ├── conftest.py              # Test configuration
│   │   ├── unit/                    # Unit tests
│   │   ├── integration/             # Integration tests
│   │   └── fixtures/                # Test data
│   ├── docs/                         # Documentation
│   ├── examples/                     # Usage examples
│   └── scripts/                      # Utility scripts
│
├── 🚀 Deployment
│   ├── deployment/                   # Deployment configurations
│   │   ├── k8s/                     # Kubernetes manifests
│   │   └── systemd/                 # Systemd service files
│   ├── Dockerfile                    # Container configuration
│   ├── docker-compose.yml           # Development environment
│   └── Makefile                     # Development tasks
│
└── 📋 Configuration
    ├── pyproject.toml               # Modern Python packaging
    ├── requirements.txt             # Production dependencies
    ├── requirements-dev.txt         # Development dependencies
    ├── .env.example                 # Environment template
    └── README.md                    # This file
```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**  
   ```bash
   cp .env.example .env
   ```  
   Edit `.env` and populate it with your API keys and credentials.

## Configuration

The following variables must be set in your `.env` file:

- `OPENAI_API_KEY` — Your OpenAI API key  
- `DEESEEK_API_KEY` — Your Deepseek API key  
- `PERPLEXITY_API_KEY` — Your Perplexity API key  
- `DEESEEK_USERNAME` / `DEESEEK_PASSWORD` — Deepseek login credentials  
- Any additional keys required by future resolvers

## Usage

1. **Start the server**  
   ```bash
   flask run --port 8000
   ```
2. **Open your browser**  
   Navigate to `http://127.0.0.1:8000/`  
3. **Enter a DOI, PMID, or title**, select the AI backend, and submit.  

## Project Structure

```plaintext
MetaFunction/
├── app.py                 # Flask application and routes
├── requirements.txt       # Python dependencies
├── .env.example           # Example env file with placeholders
├── utils/                 # Fetching/parsing resolvers
│   ├── doi_resolver.py
│   ├── pmid_resolver.py
│   ├── html_parser.py
│   └── …
├── templates/             # Jinja2 HTML templates
│   ├── index.html
│   └── layout.html
└── logs/                  # (ignored) runtime logs
```

## Development

- Add unit tests in a `tests/` directory and integrate with CI.  
- Use `flake8` or `black` for linting and formatting.  
- Implement log rotation (e.g., via `logging.handlers.RotatingFileHandler`).

## Contributing

Contributions are welcome! Please:

1. Fork the repo  
2. Create a feature branch (`git checkout -b feature/my-feature`)  
3. Commit your changes (`git commit -m 'Add new feature'`)  
4. Push to the branch (`git push origin feature/my-feature`)  
5. Open a pull request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.  
