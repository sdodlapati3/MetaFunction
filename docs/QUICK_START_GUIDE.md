# 🚀 MetaFunction Quick Start Guide

## 📋 **5-Minute Understanding**

### What is MetaFunction?
Enterprise-grade AI-powered scientific paper analysis platform that transforms research literature into actionable insights using multiple AI backends (OpenAI, DeepSeek, Perplexity).

### Key Capabilities
- **Paper Resolution**: DOI, PMID, arXiv, title → Full paper content
- **AI Analysis**: Intelligent summarization and research insights  
- **Enterprise Ready**: Kubernetes, monitoring, security, multi-region
- **Developer Friendly**: REST API, web interface, comprehensive logging

---

## 🏗️ **Repository Structure Overview**

```
MetaFunction/
├── 🚀 app.py                    # Main entry point
├── 📦 app/                      # Core application modules
│   ├── clients/                 # AI service integrations
│   ├── routes/                  # Web & API endpoints
│   ├── services/                # Business logic layer
│   └── utils/                   # Shared utilities
├── 🔍 resolvers/                # Paper resolution logic
├── 🌐 templates/ & static/      # Web interface
├── ☸️ deployment/               # Kubernetes configs
├── 📚 docs/                     # Documentation hub
├── 🗂️ archive/                  # Historical docs & configs
└── 🧪 tests/                    # Test suite
```

---

## ⚡ **Quick Setup**

```bash
# 1. Environment Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Edit .env with your API keys

# 3. Start Application
python app.py --debug
# Visit: http://localhost:5000
```

---

## 🎯 **Common Use Cases**

### Research Analysis
```bash
# Web Interface: http://localhost:5000
# Enter: DOI, PMID, arXiv ID, or paper title
# Select AI model: GPT-4, DeepSeek, Perplexity
# Get: Summary, insights, key findings
```

### API Usage
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "10.1038/nature12373", "model": "gpt-4"}'
```

---

## 📚 **Next Steps**

- **Detailed Setup**: See [README.md](../README.md)
- **Enterprise Deployment**: See [archive/documentation/ENTERPRISE_DEPLOYMENT_GUIDE.md](../archive/documentation/ENTERPRISE_DEPLOYMENT_GUIDE.md)  
- **API Reference**: See [README.md#api-reference](../README.md#-api-reference)
- **Development**: See [README.md#development](../README.md#-development)

---

*📝 For complete documentation, see [docs/README.md](README.md)*
