# 🛠️ MetaFunction Development Onboarding

## 🎯 **New Developer Quick Start** (15 minutes)

### Prerequisites
- Python 3.8+
- Git
- Basic Flask knowledge
- API keys (OpenAI/DeepSeek/Perplexity)

---

## 🚀 **Setup Process**

### 1. **Repository Setup**
```bash
git clone <repository-url>
cd MetaFunction
```

### 2. **Environment Configuration**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your_key_here
# DEEPSEEK_API_KEY=your_key_here
# PERPLEXITY_API_KEY=your_key_here
```

### 3. **Verify Installation**
```bash
# Run application
python app.py --debug

# Test basic functionality
curl http://localhost:5000/api/health
# Should return: {"status": "healthy"}
```

---

## 🗂️ **Codebase Navigation**

### **📁 Primary Working Directories**

#### **`app/`** - Core Application Logic
```
app/
├── routes/              ← Add new endpoints here
│   ├── web.py          ← Web interface routes
│   └── api.py          ← REST API endpoints
├── services/            ← Business logic layer
│   ├── ai_service.py   ← AI model management
│   ├── paper_service.py ← Paper resolution
│   └── logging_service.py ← Analytics
├── clients/             ← External service integrations
│   └── *_client.py     ← AI provider clients
└── utils/               ← Shared utilities
    ├── config.py       ← Configuration management
    └── validation.py   ← Input validation
```

#### **`resolvers/`** - Paper Resolution Logic
```
resolvers/
├── doi_resolver.py     ← DOI resolution strategies
├── pmid_resolver.py    ← PubMed integration
├── arxiv_resolver.py   ← arXiv paper handling
├── title_resolver.py  ← Title-based search
└── pdf_extractor.py   ← PDF processing
```

#### **`templates/` & `static/`** - Frontend
```
templates/
└── index.html          ← Main web interface

static/
├── css/                ← Styling
└── js/                 ← Client-side logic
```

### **📁 Supporting Directories**

- **`tests/`** - Test suite (13 core tests)
- **`deployment/`** - Kubernetes configs & scripts
- **`docs/`** - Documentation hub
- **`archive/`** - Historical docs (reference only)

---

## 🔧 **Common Development Tasks**

### **Adding a New AI Provider**

1. **Create Client** (`app/clients/new_provider_client.py`):
```python
from .ai_client import AIClient

class NewProviderClient(AIClient):
    def __init__(self, api_key):
        self.api_key = api_key
    
    def analyze_paper(self, content, model="default"):
        # Implementation here
        pass
```

2. **Register in AI Service** (`app/services/ai_service.py`):
```python
# Add to __init__ method
if 'NEW_PROVIDER_API_KEY' in os.environ:
    self.clients['new_provider'] = NewProviderClient(
        os.environ['NEW_PROVIDER_API_KEY']
    )
```

3. **Update Environment** (`.env`):
```bash
NEW_PROVIDER_API_KEY=your_key_here
```

### **Adding a New Paper Source**

1. **Create Resolver** (`resolvers/new_source_resolver.py`):
```python
def resolve_new_source(identifier):
    """Resolve papers from new source"""
    # Implementation here
    return paper_data
```

2. **Integrate in Paper Service** (`app/services/paper_service.py`):
```python
from resolvers.new_source_resolver import resolve_new_source

# Add to resolve_paper method
if identifier_type == 'new_source':
    return resolve_new_source(identifier)
```

### **Adding New API Endpoints**

1. **Define Route** (`app/routes/api.py`):
```python
@bp.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    data = request.get_json()
    # Process request
    return jsonify({"result": "success"})
```

2. **Add Business Logic** (`app/services/`):
```python
# Create new service or extend existing
def new_functionality(data):
    # Implementation here
    pass
```

---

## 🧪 **Testing Guidelines**

### **Running Tests**
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test
python -m pytest tests/test_specific.py -v
```

### **Test Structure**
```
tests/
├── test_ai_service.py      ← AI service tests
├── test_paper_service.py   ← Paper resolution tests
├── test_routes.py          ← API endpoint tests
└── test_utils.py           ← Utility function tests
```

### **Writing Tests**
```python
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_new_functionality(client):
    response = client.post('/api/test', json={'data': 'test'})
    assert response.status_code == 200
```

---

## 🔍 **Debugging & Troubleshooting**

### **Common Issues**

1. **Import Errors**
   - **Cause**: Incorrect Python path or missing dependencies
   - **Fix**: Ensure virtual environment is activated, run `pip install -r requirements.txt`

2. **API Key Issues**
   - **Cause**: Missing or invalid API keys
   - **Fix**: Check `.env` file, verify key validity

3. **Paper Resolution Failures**
   - **Cause**: External API issues or invalid identifiers
   - **Fix**: Check resolver logs, test with known working identifiers

### **Debug Mode**
```bash
# Start with debug mode
python app.py --debug

# Enable verbose logging
python app.py --log-level DEBUG

# Check application logs
tail -f logs/metafunction.log
```

### **Health Checks**
```bash
# Application health
curl http://localhost:5000/api/health

# Service-specific checks
curl http://localhost:5000/api/models  # Available AI models
curl http://localhost:5000/api/status  # Detailed status
```

---

## 📚 **Code Style & Conventions**

### **Python Style**
- **Formatter**: Black (configured in `pyproject.toml`)
- **Linter**: Flake8
- **Import Order**: isort
- **Type Hints**: Encouraged for new code

### **Git Workflow**
```bash
# Feature development
git checkout -b feature/new-feature
# Make changes
git add . && git commit -m "feat: add new feature"
git push origin feature/new-feature
# Create pull request
```

### **Commit Messages**
```
feat: add new AI provider support
fix: resolve PDF extraction issue
docs: update API documentation
refactor: improve error handling
test: add integration tests
```

---

## 🔗 **Key Resources**

### **Documentation**
- **[Architecture Overview](ARCHITECTURE_OVERVIEW.md)** - System design
- **[Quick Start Guide](QUICK_START_GUIDE.md)** - User-focused setup
- **[Main README](../README.md)** - Comprehensive documentation
- **[API Reference](../README.md#-api-reference)** - Endpoint documentation

### **Enterprise Features**
- **[Enterprise Deployment](../archive/documentation/ENTERPRISE_DEPLOYMENT_GUIDE.md)** - Production setup
- **[Kubernetes Configs](../deployment/kubernetes/)** - Container orchestration
- **[Monitoring Setup](../deployment/monitoring/)** - Observability

### **Historical Context**
- **[Project Completion Reports](../archive/documentation/)** - Transformation journey
- **[Change History](../CHANGELOG.md)** - Version evolution
- **[Legacy Documentation](../archive/)** - Historical reference

---

## 🎯 **Next Steps**

1. **Explore Codebase**: Start with `app.py` → `app/routes/` → `app/services/`
2. **Run Tests**: Understand current functionality through test cases
3. **Make Small Change**: Add a simple endpoint or modify existing functionality
4. **Read Architecture**: Understand the overall system design
5. **Check Issues**: Look for TODO comments or improvement opportunities

---

*🚀 Ready to contribute? The codebase is well-organized and ready for development!*
