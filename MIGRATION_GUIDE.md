# Code Migration Guide

This guide provides step-by-step instructions for migrating the existing monolithic `app.py` into the new modular structure.

## Migration Overview

The 1,125-line `app.py` will be split into focused, maintainable modules:

```
app.py (1,125 lines) → Multiple focused modules
├── app/main.py              # Flask app factory (~50 lines)
├── app/config.py            # Configuration management (~100 lines)
├── app/routes/web.py        # Web routes (~200 lines)
├── app/routes/api.py        # API endpoints (~150 lines)
├── app/services/paper_service.py     # Paper resolution logic (~300 lines)
├── app/services/ai_service.py        # AI model interactions (~200 lines)
├── app/clients/openai_client.py      # OpenAI API client (~100 lines)
├── app/clients/deepseek_client.py    # Deepseek API client (~75 lines)
├── app/clients/perplexity_client.py  # Perplexity API client (~75 lines)
└── app/utils/validators.py           # Validation utilities (~50 lines)
```

## Step-by-Step Migration

### Step 1: Create Flask App Factory

**Target:** `app/main.py`

Extract the Flask app initialization and create a proper app factory:

```python
# app/main.py
from flask import Flask
from app.config import get_config
from app.routes import register_routes
import logging

def create_app(config_class=None):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Initialize extensions
    from app.services.logging_service import setup_logging
    setup_logging(app)
    
    # Register routes
    register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8000)
```

**Migration from app.py:**
- Lines 78-98: Flask app initialization
- Lines 1120-1125: Main execution block

### Step 2: Extract Configuration

**Target:** `app/config.py`

Move all configuration and environment variable handling:

```python
# app/config.py
# Extract from app.py lines 78-98 and environment variable setup
```

**Migration from app.py:**
- Lines 78-98: Environment variables and API keys
- Configuration constants scattered throughout

### Step 3: Split Route Handlers

**Target:** `app/routes/web.py` and `app/routes/api.py`

Extract route handlers and split by functionality:

```python
# app/routes/web.py
from flask import Blueprint, render_template, request, session
from app.services.paper_service import PaperService
from app.services.ai_service import AIService

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Main interface route."""
    # Extract from app.py lines 408-415
    
@web_bp.route('/chat', methods=['POST'])
def chat():
    """Chat interface route."""
    # Extract from app.py lines 417-587
```

**Migration from app.py:**
- Lines 408-415: `index()` route
- Lines 417-587: `chat()` route
- Lines 589-610: Download routes
- Lines 612-650: View metadata route
- Lines 950-1118: Test sources route

### Step 4: Create Service Layer

**Target:** `app/services/paper_service.py`

Extract paper resolution and processing logic:

```python
# app/services/paper_service.py
class PaperService:
    """Service for paper resolution and processing."""
    
    def resolve_paper(self, query: str):
        """Resolve paper from DOI, PMID, or title."""
        # Extract logic from app.py chat() function
        
    def extract_identifiers(self, query: str):
        """Extract DOI, PMID from query."""
        # Extract from app.py lines 440-490
        
    def get_full_text(self, doi: str = None, pmid: str = None):
        """Get full text using multiple resolvers."""
        # Extract from app.py lines 490-530
```

**Migration from app.py:**
- Lines 440-530: Paper identifier extraction and resolution
- Integration with utils/full_text_resolver.py
- Metadata processing logic

### Step 5: Create AI Service

**Target:** `app/services/ai_service.py`

Extract AI model interaction logic:

```python
# app/services/ai_service.py
class AIService:
    """Service for AI model interactions."""
    
    def __init__(self):
        self.clients = {
            'openai': OpenAIClient(),
            'deepseek': DeepSeekClient(),
            'perplexity': PerplexityClient()
        }
    
    def get_response(self, model: str, prompt: str):
        """Get response from specified model."""
        # Extract from app.py lines 165-200
```

**Migration from app.py:**
- Lines 165-200: `get_model_response()` function
- Lines 250-290: Model availability logic
- Cache management logic

### Step 6: Create API Clients

**Target:** `app/clients/` directory

Extract external API client logic:

```python
# app/clients/openai_client.py
class OpenAIClient:
    """OpenAI API client."""
    # Extract from app.py lines 140-165

# app/clients/deepseek_client.py
class DeepSeekClient:
    """Deepseek API client."""
    # Extract from app.py lines 1050-1090

# app/clients/perplexity_client.py
class PerplexityClient:
    """Perplexity API client."""
    # Extract from app.py lines 1090-1118
```

**Migration from app.py:**
- Lines 140-165: OpenAI client logic
- Lines 1050-1090: Deepseek client logic
- Lines 1090-1118: Perplexity client logic

### Step 7: Extract Utilities

**Target:** `app/utils/` directory

Move utility functions:

```python
# app/utils/validators.py
def validate_doi(doi: str) -> bool:
    """Validate DOI format."""
    # Extract from utils/full_text_resolver.py

# app/utils/formatters.py
def clean_text(text: str) -> str:
    """Clean and format text."""
    # Extract from app.py lines 120-125
```

**Migration from app.py:**
- Lines 120-135: Helper functions (`clean_text`, `clean_doi`, `safe_api_call`)
- Validation logic scattered throughout

### Step 8: Enhance Logging

**Target:** `app/services/logging_service.py`

Centralize logging configuration:

```python
# app/services/logging_service.py
class LoggingService:
    """Centralized logging service."""
    
    def setup_logging(self, app):
        """Configure application logging."""
        # Extract from app.py lines 101-115
        
    def log_chat(self, session_id, user_input, response, metadata):
        """Log chat interactions."""
        # Extract from app.py lines 200-250
```

**Migration from app.py:**
- Lines 101-115: Logging setup
- Lines 200-250: Chat logging logic
- Lines 250-280: Metadata logging logic

## Migration Checklist

### Pre-Migration
- [ ] Create backup of current repository
- [ ] Run existing tests to establish baseline
- [ ] Document current API endpoints
- [ ] Review environment variable usage

### During Migration
- [ ] Create new directory structure
- [ ] Migrate configuration management
- [ ] Extract and test Flask app factory
- [ ] Split route handlers by functionality
- [ ] Create service layer with dependency injection
- [ ] Extract API clients with proper error handling
- [ ] Move utilities to focused modules
- [ ] Update imports throughout codebase

### Post-Migration
- [ ] Update all import statements
- [ ] Ensure all tests pass
- [ ] Update documentation
- [ ] Verify environment variable mapping
- [ ] Test API endpoints functionality
- [ ] Performance testing
- [ ] Update deployment scripts

## Testing During Migration

Each migration step should include:

1. **Unit Tests**: Test individual functions/classes
2. **Integration Tests**: Test module interactions
3. **API Tests**: Verify endpoint functionality
4. **Regression Tests**: Ensure existing functionality works

Example test structure:
```python
# tests/unit/test_paper_service.py
def test_extract_doi_from_query():
    service = PaperService()
    doi = service.extract_identifiers("Check paper with DOI 10.1000/test")
    assert doi == "10.1000/test"

# tests/integration/test_paper_pipeline.py
def test_full_paper_resolution():
    service = PaperService()
    result = service.resolve_paper("10.1000/test.doi")
    assert result.has_metadata
    assert result.text_length > 0
```

## Common Issues and Solutions

### Import Circular Dependencies
**Problem**: Modules importing each other
**Solution**: Use dependency injection and interface patterns

### Configuration Management
**Problem**: Environment variables scattered throughout code
**Solution**: Centralize in config.py with type hints and validation

### Database/Session Management
**Problem**: Global state in Flask sessions
**Solution**: Proper session management in service layer

### Error Handling
**Problem**: Inconsistent error handling across modules
**Solution**: Custom exception classes and centralized error handlers

## Validation Steps

After migration, verify:

1. **Functionality**: All features work as before
2. **Performance**: No significant performance degradation
3. **Maintainability**: Code is easier to understand and modify
4. **Testability**: Higher test coverage is achievable
5. **Documentation**: Clear module responsibilities

## Timeline Estimate

- **Phase 1** (Days 1-2): Directory structure and configuration
- **Phase 2** (Days 3-4): Flask app factory and route extraction
- **Phase 3** (Days 5-6): Service layer creation
- **Phase 4** (Days 7-8): API client extraction
- **Phase 5** (Days 9-10): Testing and validation

This migration will transform the codebase from a monolithic structure to a maintainable, testable, and scalable architecture while preserving all existing functionality.
