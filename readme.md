# MetaFunction

MetaFunction is a Flask-based web application for AI-powered summarization and content extraction of scientific papers. It supports querying by DOI, PMID, or title and integrates with multiple backend models (OpenAI, Deepseek, Perplexity). Its modular design cleanly separates fetch/parsing logic and the web interface.

## Features

- Summarize papers via DOI, PMID, or title lookup  
- Fetch full-text HTML or PDF from multiple sources  
- Switchable AI backends: OpenAI, Deepseek, Perplexity  
- Extensible resolver framework in `utils/`  
- Simple web interface built on Flask  

## Prerequisites

- Python 3.8 or later  
- `git` and `pip` installed  

## Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/SanjeevaRDodlapati/MetaFunction.git
   cd MetaFunction
   ```

2. **Create and activate a virtual environment**  
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate    # Windows
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
