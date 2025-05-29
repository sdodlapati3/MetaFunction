# 🗺️ MetaFunction Architecture Overview

## 🎯 **System Architecture at a Glance**

MetaFunction follows a **modern, enterprise-grade, microservices-inspired** architecture built on Flask with clear separation of concerns.

---

## 🏗️ **High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                     │
│  ┌──────────────────┐    ┌──────────────────────────────────────┐│
│  │   Web Interface  │    │            REST API                  ││
│  │  (templates/)    │    │         (app/routes/)                ││
│  │  - index.html    │    │   - /api/analyze                     ││
│  │  - Enhanced UI   │    │   - /api/health                      ││
│  └──────────────────┘    └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │   AI Service │ │Paper Service │ │Logger Service│ │Config  ││
│  │  (services/) │ │  (services/) │ │  (services/) │ │Manager ││
│  │              │ │              │ │              │ │        ││
│  │• Model Mgmt  │ │• Resolution  │ │• Structured  │ │• Env   ││
│  │• API Clients │ │• Validation  │ │• Analytics   │ │• SSL   ││
│  │• Load Balance│ │• Caching     │ │• Monitoring  │ │• Debug ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘│
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Resolution Layer                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │DOI Resolver  │ │PMID Resolver │ │arXiv Resolver│ │Title   ││
│  │              │ │              │ │              │ │Resolver││
│  │• CrossRef    │ │• PubMed      │ │• arXiv API   │ │• Multi ││
│  │• Official    │ │• Official    │ │• Official    │ │• Search││
│  │• Fallbacks   │ │• Fallbacks   │ │• Fallbacks   │ │• Logic ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘│
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Client Layer                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │OpenAI Client │ │DeepSeek      │ │Perplexity    │ │PDF     ││
│  │              │ │Client        │ │Client        │ │Extract ││
│  │• GPT-4       │ │• DeepSeek    │ │• Claude-like │ │• PyMuPDF││
│  │• GPT-3.5     │ │• R1 Models   │ │• Sonar       │ │• Fallbck││
│  │• Rate Limit  │ │• Rate Limit  │ │• Rate Limit  │ │• OCR   ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 **Core Components**

### 1. **Entry Point** (`app.py`)
- **Purpose**: Clean application startup and CLI interface
- **Features**: Environment validation, debug options, SSL configuration
- **Size**: ~140 lines (down from 2000+ in legacy)

### 2. **Application Core** (`app/`)
```
app/
├── __init__.py          # Flask app factory
├── clients/             # External service integrations
│   ├── ai_client.py    # AI service abstraction
│   ├── openai_client.py
│   ├── deepseek_client.py
│   └── perplexity_client.py
├── routes/              # HTTP endpoints
│   ├── web.py          # Web interface routes
│   └── api.py          # REST API endpoints
├── services/            # Business logic
│   ├── ai_service.py   # AI model management
│   ├── paper_service.py # Paper resolution coordination
│   └── logging_service.py # Analytics and monitoring
└── utils/               # Shared utilities
    ├── config.py       # Configuration management
    ├── validation.py   # Input validation
    └── helpers.py      # Common functions
```

### 3. **Resolution Engine** (`resolvers/`)
```
resolvers/
├── doi_resolver.py     # DOI-based paper resolution
├── pmid_resolver.py    # PubMed ID resolution
├── arxiv_resolver.py   # arXiv paper resolution
├── title_resolver.py  # Title-based search
└── pdf_extractor.py   # PDF content extraction
```

### 4. **Enterprise Infrastructure** (`deployment/`)
```
deployment/
├── kubernetes/         # K8s manifests (28 files)
├── monitoring/         # Prometheus, Grafana configs
├── security/          # Security policies, Falco rules
└── scripts/           # Deployment automation
```

---

## 🔄 **Data Flow**

### Paper Analysis Request Flow:
```
1. User Input → Web UI or API
2. Input Validation → Utils layer
3. Paper Resolution → Resolvers layer
4. Content Extraction → PDF/Text processing
5. AI Analysis → AI clients layer
6. Response Formation → Services layer
7. Logging & Analytics → Logging service
8. Response Delivery → User interface
```

### Model Selection Flow:
```
1. User selects model → AI Service
2. Client routing → Appropriate AI client
3. Load balancing → Rate limiting
4. API request → External AI service
5. Response processing → Error handling
6. Result caching → Performance optimization
```

---

## 🎯 **Design Principles**

### 1. **Separation of Concerns**
- **Routes**: Handle HTTP requests/responses only
- **Services**: Contain business logic and coordination
- **Clients**: Handle external service communication
- **Resolvers**: Focused on paper resolution strategies

### 2. **Dependency Injection**
- Services injected into routes
- Clients injected into services
- Configuration injected throughout

### 3. **Error Handling**
- Comprehensive exception hierarchy
- Graceful fallbacks for external services
- Structured error responses

### 4. **Enterprise Patterns**
- **Factory Pattern**: Flask app factory
- **Strategy Pattern**: Multiple AI providers
- **Adapter Pattern**: External service clients
- **Observer Pattern**: Logging and monitoring

---

## 🚀 **Scalability Features**

### Horizontal Scaling
- **Stateless Design**: No server-side sessions
- **Load Balancing**: Multiple AI provider support
- **Kubernetes Ready**: HPA and VPA configured

### Performance Optimization
- **Caching**: Response caching for repeated queries
- **Connection Pooling**: Efficient API client management
- **Lazy Loading**: On-demand service initialization

### Monitoring & Observability
- **Structured Logging**: JSON-formatted logs
- **Metrics Collection**: Prometheus integration
- **Distributed Tracing**: Jaeger support
- **Health Checks**: Kubernetes liveness/readiness probes

---

## 📊 **Technical Stack**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | Flask 2.3+ | Web application framework |
| **Architecture** | Blueprint-based | Modular route organization |
| **AI Integration** | OpenAI, DeepSeek, Perplexity | Multiple AI provider support |
| **Paper Resolution** | CrossRef, PubMed, arXiv APIs | Multi-source paper discovery |
| **Container** | Docker + Kubernetes | Containerization and orchestration |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Security** | Falco + OPA | Runtime security and policies |

---

*📚 For detailed implementation, see [README.md](../README.md) and [archive/documentation/](../archive/documentation/)*
