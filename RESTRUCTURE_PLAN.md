# MetaFunction Repository Restructuring Plan

## Overview
This document outlines a comprehensive plan to refactor the MetaFunction repository into a more maintainable, scalable, and professional structure.

## Current Issues
- **Monolithic app.py**: 1,125 lines mixing routing, business logic, and utilities
- **No testing framework**: Missing tests and CI/CD
- **Configuration scattered**: Environment variables and settings mixed throughout
- **Documentation inconsistencies**: DEEPSEEK vs DEESEEK naming, missing API docs
- **No proper package structure**: Missing `__init__.py` files

## Proposed New Structure

```
MetaFunction/
├── README.md                          # Updated comprehensive documentation
├── requirements.txt                   # Dependencies (separated by environment)
├── requirements-dev.txt               # Development dependencies
├── pyproject.toml                     # Modern Python packaging and tool config
├── .env.example                       # Environment template
├── .gitignore                         # Enhanced gitignore
├── Dockerfile                         # Container support
├── docker-compose.yml                 # Development environment
├── Makefile                           # Common development tasks
│
├── app/                               # Main application package
│   ├── __init__.py                    # Package initialization
│   ├── main.py                        # Flask app factory and entry point
│   ├── config.py                      # Configuration management
│   ├── models/                        # Data models and schemas
│   │   ├── __init__.py
│   │   ├── paper.py                   # Paper metadata models
│   │   └── chat.py                    # Chat/session models
│   ├── routes/                        # Flask route handlers
│   │   ├── __init__.py
│   │   ├── api.py                     # API endpoints
│   │   ├── web.py                     # Web interface routes
│   │   └── admin.py                   # Administrative routes
│   ├── services/                      # Business logic layer
│   │   ├── __init__.py
│   │   ├── paper_service.py           # Paper resolution and processing
│   │   ├── ai_service.py              # AI model interactions
│   │   ├── cache_service.py           # Caching logic
│   │   └── logging_service.py         # Structured logging
│   ├── clients/                       # External API clients
│   │   ├── __init__.py
│   │   ├── openai_client.py           # OpenAI API client
│   │   ├── deepseek_client.py         # Deepseek API client
│   │   ├── perplexity_client.py       # Perplexity API client
│   │   └── base_client.py             # Base client with common functionality
│   └── utils/                         # Application utilities
│       ├── __init__.py
│       ├── validators.py              # Input validation
│       ├── formatters.py              # Response formatting
│       └── exceptions.py              # Custom exceptions
│
├── resolvers/                         # Paper content resolution (existing utils/)
│   ├── __init__.py
│   ├── base_resolver.py               # Base resolver interface
│   ├── pubmed_resolver.py             # PubMed/PMC resolution
│   ├── doi_resolver.py                # DOI-based resolution
│   ├── institutional_resolver.py     # Institutional access
│   ├── pdf_extractor.py              # PDF text extraction
│   └── browser_extractor.py          # Browser-based extraction
│
├── static/                            # Static web assets
│   ├── css/
│   │   ├── main.css                   # Main stylesheet
│   │   └── compact.css                # Ultra-compact theme
│   ├── js/
│   │   ├── main.js                    # Main JavaScript
│   │   ├── markdown.js                # Markdown rendering
│   │   └── api.js                     # API interaction
│   └── images/                        # Images and icons
│
├── templates/                         # Jinja2 templates
│   ├── base.html                      # Base template
│   ├── index.html                     # Main interface
│   ├── test_sources.html              # Source testing
│   ├── admin/                         # Admin templates
│   │   ├── dashboard.html
│   │   └── logs.html
│   └── components/                    # Reusable components
│       ├── paper_info.html
│       └── model_selector.html
│
├── tests/                             # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                    # Test configuration
│   ├── unit/                          # Unit tests
│   │   ├── test_resolvers.py
│   │   ├── test_services.py
│   │   ├── test_clients.py
│   │   └── test_utils.py
│   ├── integration/                   # Integration tests
│   │   ├── test_api_endpoints.py
│   │   └── test_paper_pipeline.py
│   └── fixtures/                      # Test data
│       ├── sample_papers.json
│       └── mock_responses.json
│
├── docs/                              # Documentation
│   ├── API.md                         # API documentation
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── DEVELOPMENT.md                 # Development setup
│   ├── ARCHITECTURE.md                # System architecture
│   └── CHANGELOG.md                   # Version history
│
├── scripts/                           # Utility scripts
│   ├── setup_dev.py                   # Development environment setup
│   ├── migrate_data.py                # Data migration scripts
│   └── benchmark_resolvers.py         # Performance testing
│
├── logs/                              # Application logs (gitignored)
│   ├── .gitkeep
│   └── README.md                      # Log file descriptions
│
└── deployment/                        # Deployment configurations
    ├── nginx.conf                     # Nginx configuration
    ├── gunicorn.conf.py               # Gunicorn configuration
    ├── systemd/                       # Systemd service files
    └── k8s/                           # Kubernetes manifests
```

## Implementation Phases

### Phase 1: Core Restructuring (Week 1)
1. Create new directory structure
2. Split app.py into logical modules
3. Implement configuration management
4. Set up package initialization

### Phase 2: Testing Framework (Week 2)
1. Set up pytest framework
2. Create unit tests for core functionality
3. Add integration tests
4. Implement CI/CD pipeline

### Phase 3: API & Documentation (Week 3)
1. Create proper REST API endpoints
2. Add comprehensive documentation
3. Implement OpenAPI/Swagger spec
4. Create development guides

### Phase 4: Enhancement & Optimization (Week 4)
1. Add caching layer improvements
2. Implement rate limiting
3. Add monitoring and metrics
4. Performance optimization

## Benefits of Restructuring

### Developer Experience
- **Maintainability**: Smaller, focused modules are easier to understand and modify
- **Testability**: Separated concerns enable comprehensive unit testing
- **Collaboration**: Clear structure allows multiple developers to work simultaneously
- **Debugging**: Isolated components simplify troubleshooting

### Code Quality
- **Single Responsibility**: Each module has a clear, focused purpose
- **Dependency Injection**: Services can be easily mocked and tested
- **Error Handling**: Centralized exception handling and logging
- **Type Safety**: Better IDE support and static analysis

### Scalability
- **Horizontal Scaling**: Modular design supports microservices migration
- **Feature Addition**: New resolvers and AI clients can be added easily
- **Configuration Management**: Environment-specific settings are centralized
- **Performance Monitoring**: Built-in metrics and profiling capabilities

## Migration Strategy

### Backward Compatibility
- Maintain existing API endpoints during transition
- Gradual migration with feature flags
- Comprehensive testing at each step
- Database migration scripts if needed

### Risk Mitigation
- Feature branches for each phase
- Automated testing before merging
- Rollback procedures documented
- Performance monitoring during migration

## Next Steps

1. **Approve Structure**: Review and approve the proposed structure
2. **Create Branch**: Create a `restructure` branch for development
3. **Start Phase 1**: Begin with core restructuring
4. **Set Up CI**: Implement automated testing and deployment
5. **Documentation**: Update all documentation to reflect new structure

This restructuring will transform MetaFunction from a monolithic Flask app into a professional, maintainable, and scalable scientific paper analysis platform.
