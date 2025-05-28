# 📚 MetaFunction Usage Guide

## 🚀 How to Use MetaFunction

MetaFunction is an AI-powered scientific paper analysis tool that helps you summarize and extract insights from research papers. Here's how to use it:

## 🛠️ Setup & Installation

### 1. **Prerequisites**
- Python 3.8 or later
- pip package manager
- API keys for AI services

### 2. **Installation**
```bash
# Clone the repository
git clone https://github.com/SanjeevaRDodlapati/MetaFunction.git
cd MetaFunction

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR
.\.venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. **Configuration**
Set up your environment variables (create a `.env` file or export them):

```bash
# Required API Keys
export OPENAI_API_KEY="your-openai-api-key"
export DEEPSEEK_API_KEY="your-deepseek-api-key"
export PERPLEXITY_API_KEY="your-perplexity-api-key"

# Optional API Keys (for enhanced paper access)
export SERPAPI_API_KEY="your-serpapi-key"
export SCOPUS_API_KEY="your-scopus-key"
export SPRINGER_API_KEY="your-springer-key"

# Academic Settings
export NCBI_EMAIL="your-email@example.com"
export CROSSREF_EMAIL="your-email@example.com"

# Flask Settings
export FLASK_ENV="development"  # or "production"
export SECRET_KEY="your-secret-key"
```

## 🖥️ Running the Application

### **Development Mode**
```bash
python -m flask --app app.main:create_app run --debug --port 5000
```

### **Production Mode**
```bash
# Using Gunicorn (recommended for production)
gunicorn "app.main:create_app()" --bind 0.0.0.0:5000 --workers 4

# Or using Flask directly
python -m flask --app app.main:create_app run --host 0.0.0.0 --port 5000
```

### **Using Docker**
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t metafunction .
docker run -p 5000:5000 --env-file .env metafunction
```

## 🌐 Web Interface Usage

### **Main Interface** (`http://localhost:5000/`)

1. **Enter Paper Information**:
   - **DOI**: `10.1038/nature12373`
   - **PMID**: `23842501`
   - **Paper Title**: "A complete genome sequence of Neanderthal"
   - **arXiv ID**: `2301.12345`

2. **Select AI Model**:
   - **GPT-4o** (most capable, higher cost)
   - **GPT-4o-mini** (fast, cost-effective)
   - **DeepSeek Chat** (good alternative)
   - **Perplexity** (web-enhanced responses)

3. **Ask Questions**:
   - "Summarize the main findings"
   - "What are the key methodologies used?"
   - "What are the limitations of this study?"
   - "How does this relate to previous research?"

### **Additional Features**

- **📊 View Metadata** (`/view_metadata`): See paper metadata and analysis history
- **📁 Download Logs** (`/download_log`): Export chat interaction logs
- **🔍 Test Sources** (`/test_sources`): Test paper source availability
- **💚 Health Check** (`/health`): Check application status

## 🔌 API Usage

### **Available Endpoints**

#### **1. Get Available Models**
```bash
curl http://localhost:5000/api/models
```

#### **2. Analyze Paper**
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the main findings",
    "paper_input": "10.1038/nature12373",
    "model": "gpt-4o-mini",
    "session_id": "user123"
  }'
```

#### **3. Resolve Paper Information**
```bash
curl -X POST http://localhost:5000/api/paper/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "paper_input": "10.1038/nature12373"
  }'
```

#### **4. Test Paper Sources**
```bash
curl -X POST http://localhost:5000/api/paper/test_sources \
  -H "Content-Type: application/json" \
  -d '{
    "paper_input": "10.1038/nature12373"
  }'
```

## 📝 Example Usage Scenarios

### **Scenario 1: Research Paper Summary**
1. Go to `http://localhost:5000/`
2. Enter DOI: `10.1126/science.1240672`
3. Select model: `gpt-4o-mini`
4. Ask: "Provide a comprehensive summary of this paper including methods, results, and conclusions"

### **Scenario 2: Methodology Analysis**
1. Enter paper identifier
2. Ask: "What statistical methods were used in this study? Are they appropriate for the research questions?"

### **Scenario 3: Literature Context**
1. Enter paper identifier  
2. Ask: "How does this work compare to previous studies in the field? What gaps does it fill?"

### **Scenario 4: Critical Analysis**
1. Enter paper identifier
2. Ask: "What are the strengths and limitations of this study? What future research directions are suggested?"

## 🔧 Advanced Configuration

### **Model Selection Guidelines**
- **GPT-4o**: Best for complex analysis, detailed summaries
- **GPT-4o-mini**: Good balance of speed and quality, cost-effective
- **DeepSeek**: Good alternative, often faster
- **Perplexity**: Enhanced with web search, good for recent papers

### **Performance Optimization**
```bash
# Set cache size for better performance
export CACHE_SIZE=200

# Adjust log level
export LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR
```

### **Logging and Monitoring**
- **Application logs**: `logs/application.log`
- **Chat interactions**: `logs/chat_logs.csv`
- **Metadata**: `logs/metadata_log.json`

## 🚨 Troubleshooting

### **Common Issues**

1. **API Key Errors**:
   ```
   Error: Missing API key for model
   ```
   **Solution**: Ensure all required API keys are set in environment variables

2. **Paper Not Found**:
   ```
   Error: Could not resolve paper
   ```
   **Solution**: Try different identifier format (DOI vs PMID vs title)

3. **Model Not Available**:
   ```
   Error: Unsupported model
   ```
   **Solution**: Check available models at `/api/models` endpoint

4. **Server Won't Start**:
   ```
   Error: Address already in use
   ```
   **Solution**: Change port or kill existing process:
   ```bash
   lsof -ti:5000 | xargs kill  # Kill process on port 5000
   python -m flask --app app.main:create_app run --port 5001  # Use different port
   ```

### **Debug Mode**
```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
python -m flask --app app.main:create_app run --debug
```

## 📊 Features Overview

### ✅ **Supported Paper Sources**
- DOI resolution via CrossRef
- PubMed (PMID) integration
- arXiv paper support
- Direct PDF processing
- HTML content extraction

### ✅ **AI Models Supported**
- OpenAI (GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo)
- DeepSeek (deepseek-chat, deepseek-coder)
- Perplexity (Llama models with web search)

### ✅ **Analysis Capabilities**
- Paper summarization
- Methodology analysis
- Results interpretation
- Limitations assessment
- Literature context analysis
- Custom queries

### ✅ **Web Interface Features**
- Clean, responsive design
- Real-time chat interface
- Model selection
- Download capabilities
- Health monitoring

### ✅ **API Features**
- RESTful API design
- JSON request/response format
- Error handling
- Session management
- Comprehensive logging

## 🎯 Best Practices

1. **Use appropriate models**: GPT-4o-mini for most tasks, GPT-4o for complex analysis
2. **Be specific in queries**: Ask targeted questions for better results
3. **Monitor usage**: Check logs regularly for performance insights
4. **Keep API keys secure**: Use environment variables, never commit keys to code
5. **Regular updates**: Keep dependencies updated for security and performance

## 📞 Support

For issues, feature requests, or contributions:
- **GitHub Issues**: Create an issue in the repository
- **Documentation**: Check RESTRUCTURE_COMPLETE.md for technical details
- **Logs**: Check application logs for detailed error information

---

**Ready to analyze papers! 🎉**

Visit `http://localhost:5000/` to start using MetaFunction!
